# Алгоритмы сжатия и декомпрессии в форматах моделей Valve

## Обзор методов сжатия

Source Engine использует несколько методов оптимизации и сжатия данных в форматах моделей:

1. **Vertex Cache Optimization** - оптимизация для аппаратного кэша вершин
2. **Triangle Strip Encoding** - кодирование треугольников в виде полос
3. **Bone Weight Quantization** - квантование весов костей
4. **LOD Progressive Meshes** - прогрессивные меши для уровней детализации
5. **Fixup Tables** - таблицы коррекции для различных LOD

## 1. Vertex Cache Optimization

### 1.1 Принцип работы

Современные GPU имеют кэш вершин размером 16-32 элемента. VTX файлы организуют треугольники для максимального использования этого кэша.

```c
// Структура для отслеживания кэша вершин
struct VertexCache {
    int cache[VERTEX_CACHE_SIZE];
    int cachePos;
    int cacheMisses;
    int cacheHits;
};

// Алгоритм оптимизации порядка треугольников
void OptimizeTriangleOrder(Triangle* triangles, int numTriangles) {
    VertexCache cache = {0};
    
    for (int i = 0; i < numTriangles; i++) {
        Triangle& tri = triangles[i];
        
        // Проверяем каждую вершину треугольника
        for (int v = 0; v < 3; v++) {
            int vertexIndex = tri.vertices[v];
            
            if (!IsInCache(&cache, vertexIndex)) {
                // Cache miss - добавляем вершину в кэш
                AddToCache(&cache, vertexIndex);
                cache.cacheMisses++;
            } else {
                cache.cacheHits++;
            }
        }
    }
}
```

### 1.2 Метрики оптимизации

```c
// Расчет эффективности кэша
float CalculateCacheEfficiency(int cacheHits, int cacheMisses) {
    int totalAccesses = cacheHits + cacheMisses;
    return (float)cacheHits / totalAccesses;
}

// Средний размер triangle strip
float CalculateAverageStripLength(StripGroup* stripGroups, int numStripGroups) {
    int totalTriangles = 0;
    int totalStrips = 0;
    
    for (int i = 0; i < numStripGroups; i++) {
        totalStrips += stripGroups[i].numStrips;
        totalTriangles += stripGroups[i].numIndices / 3;
    }
    
    return (float)totalTriangles / totalStrips;
}
```

## 2. Triangle Strip Encoding

### 2.1 Алгоритм кодирования

Triangle strips позволяют представить N треугольников используя N+2 вершины вместо 3N.

```c
// Структура triangle strip
struct TriangleStrip {
    unsigned short* indices;
    int numIndices;
    bool clockwise;
};

// Кодирование треугольников в strip
TriangleStrip EncodeTriangleStrip(Triangle* triangles, int numTriangles) {
    TriangleStrip strip;
    strip.indices = new unsigned short[numTriangles + 2];
    strip.numIndices = 0;
    strip.clockwise = true;
    
    if (numTriangles == 0) return strip;
    
    // Первый треугольник
    Triangle& firstTri = triangles[0];
    strip.indices[0] = firstTri.v0;
    strip.indices[1] = firstTri.v1;
    strip.indices[2] = firstTri.v2;
    strip.numIndices = 3;
    
    // Добавляем остальные треугольники
    for (int i = 1; i < numTriangles; i++) {
        Triangle& tri = triangles[i];
        
        // Находим общее ребро с предыдущим треугольником
        int sharedVerts = FindSharedVertices(triangles[i-1], tri);
        
        if (sharedVerts == 2) {
            // Можем продолжить strip
            int newVertex = FindNewVertex(triangles[i-1], tri);
            strip.indices[strip.numIndices++] = newVertex;
        } else {
            // Нужно начать новый strip
            break;
        }
    }
    
    return strip;
}
```

### 2.2 Декодирование triangle strips

```c
// Декодирование strip в треугольники
void DecodeTriangleStrip(TriangleStrip& strip, Triangle* outTriangles, int& numTriangles) {
    numTriangles = 0;
    
    if (strip.numIndices < 3) return;
    
    for (int i = 0; i < strip.numIndices - 2; i++) {
        unsigned short v0 = strip.indices[i];
        unsigned short v1 = strip.indices[i + 1];
        unsigned short v2 = strip.indices[i + 2];
        
        // Пропускаем вырожденные треугольники
        if (v0 == v1 || v1 == v2 || v0 == v2) {
            continue;
        }
        
        Triangle& tri = outTriangles[numTriangles++];
        
        // Чередуем порядок вершин для правильной ориентации
        if (i % 2 == 0) {
            tri.v0 = v0; tri.v1 = v1; tri.v2 = v2;
        } else {
            tri.v0 = v0; tri.v1 = v2; tri.v2 = v1;
        }
    }
}
```

## 3. Bone Weight Quantization

### 3.1 Квантование весов

Веса костей квантуются для экономии памяти и повышения производительности.

```c
// Квантование весов костей
struct QuantizedBoneWeight {
    unsigned char weights[MAX_BONES_PER_VERT]; // 0-255
    unsigned char bones[MAX_BONES_PER_VERT];   // Индексы костей
    unsigned char numBones;
};

// Конвертация float весов в квантованные
QuantizedBoneWeight QuantizeBoneWeights(float* weights, int* bones, int numBones) {
    QuantizedBoneWeight quantized = {0};
    quantized.numBones = numBones;
    
    // Нормализуем веса
    float totalWeight = 0.0f;
    for (int i = 0; i < numBones; i++) {
        totalWeight += weights[i];
    }
    
    if (totalWeight > 0.0f) {
        for (int i = 0; i < numBones; i++) {
            weights[i] /= totalWeight;
        }
    }
    
    // Квантуем в диапазон 0-255
    int totalQuantized = 0;
    for (int i = 0; i < numBones - 1; i++) {
        quantized.weights[i] = (unsigned char)(weights[i] * 255.0f);
        quantized.bones[i] = bones[i];
        totalQuantized += quantized.weights[i];
    }
    
    // Последний вес - остаток для точной нормализации
    quantized.weights[numBones - 1] = 255 - totalQuantized;
    quantized.bones[numBones - 1] = bones[numBones - 1];
    
    return quantized;
}

// Деквантование весов
void DequantizeBoneWeights(QuantizedBoneWeight& quantized, float* outWeights, int* outBones) {
    for (int i = 0; i < quantized.numBones; i++) {
        outWeights[i] = quantized.weights[i] / 255.0f;
        outBones[i] = quantized.bones[i];
    }
}
```

## 4. LOD Progressive Meshes

### 4.1 Алгоритм упрощения мешей

```c
// Структура для edge collapse
struct EdgeCollapse {
    int vertexA, vertexB;    // Вершины ребра
    int targetVertex;        // Результирующая вершина
    float cost;              // Стоимость операции
    Vector3 newPosition;     // Новая позиция вершины
};

// Генерация LOD уровней
void GenerateLODLevels(Mesh& originalMesh, Mesh* lodMeshes, int numLODs) {
    lodMeshes[0] = originalMesh; // LOD 0 - оригинальный меш
    
    for (int lod = 1; lod < numLODs; lod++) {
        Mesh& prevLOD = lodMeshes[lod - 1];
        Mesh& currentLOD = lodMeshes[lod];
        
        // Целевое количество вершин для этого LOD
        int targetVertices = originalMesh.numVertices >> lod;
        
        // Упрощаем меш до целевого количества вершин
        SimplifyMesh(prevLOD, currentLOD, targetVertices);
    }
}

// Упрощение меша методом edge collapse
void SimplifyMesh(Mesh& inputMesh, Mesh& outputMesh, int targetVertices) {
    std::vector<EdgeCollapse> collapses;
    
    // Находим все возможные edge collapses
    for (int i = 0; i < inputMesh.numEdges; i++) {
        Edge& edge = inputMesh.edges[i];
        EdgeCollapse collapse = CalculateEdgeCollapse(inputMesh, edge);
        collapses.push_back(collapse);
    }
    
    // Сортируем по стоимости (от меньшей к большей)
    std::sort(collapses.begin(), collapses.end(), 
              [](const EdgeCollapse& a, const EdgeCollapse& b) {
                  return a.cost < b.cost;
              });
    
    // Применяем collapses пока не достигнем целевого количества вершин
    outputMesh = inputMesh;
    int currentVertices = inputMesh.numVertices;
    
    for (const EdgeCollapse& collapse : collapses) {
        if (currentVertices <= targetVertices) break;
        
        ApplyEdgeCollapse(outputMesh, collapse);
        currentVertices--;
    }
}
```

### 4.2 Расчет стоимости edge collapse

```c
// Расчет стоимости сжатия ребра
float CalculateEdgeCollapseCost(Mesh& mesh, Edge& edge) {
    Vector3 posA = mesh.vertices[edge.vertexA].position;
    Vector3 posB = mesh.vertices[edge.vertexB].position;
    
    // Базовая стоимость - длина ребра
    float baseCost = Distance(posA, posB);
    
    // Штраф за изменение кривизны поверхности
    float curvaturePenalty = CalculateCurvaturePenalty(mesh, edge);
    
    // Штраф за изменение границ
    float boundaryPenalty = CalculateBoundaryPenalty(mesh, edge);
    
    // Штраф за изменение UV координат
    float uvPenalty = CalculateUVPenalty(mesh, edge);
    
    return baseCost + curvaturePenalty + boundaryPenalty + uvPenalty;
}
```

## 5. Fixup Tables для LOD

### 5.1 Структура Fixup Table

```c
// Запись в таблице коррекции
struct VertexFixup {
    int sourceVertexIndex;    // Индекс в исходном меше
    int lodVertexIndex;       // Индекс в LOD меше
    float weight;             // Вес интерполяции
};

// Таблица коррекции для LOD
struct LODFixupTable {
    VertexFixup* fixups;
    int numFixups;
    int sourceLOD;            // Исходный LOD
    int targetLOD;            // Целевой LOD
};
```

### 5.2 Применение Fixup Table

```c
// Применение коррекций при переходе между LOD
void ApplyLODFixups(Mesh& mesh, LODFixupTable& fixupTable) {
    for (int i = 0; i < fixupTable.numFixups; i++) {
        VertexFixup& fixup = fixupTable.fixups[i];
        
        // Интерполируем позицию вершины
        Vector3 sourcePos = mesh.vertices[fixup.sourceVertexIndex].position;
        Vector3 targetPos = mesh.vertices[fixup.lodVertexIndex].position;
        
        mesh.vertices[fixup.lodVertexIndex].position = 
            Lerp(sourcePos, targetPos, fixup.weight);
        
        // Интерполируем нормали
        Vector3 sourceNormal = mesh.vertices[fixup.sourceVertexIndex].normal;
        Vector3 targetNormal = mesh.vertices[fixup.lodVertexIndex].normal;
        
        mesh.vertices[fixup.lodVertexIndex].normal = 
            Normalize(Lerp(sourceNormal, targetNormal, fixup.weight));
    }
}
```

## 6. Алгоритмы декомпрессии в реальном времени

### 6.1 Потоковая декомпрессия

```c
// Потоковый декодер для VTX данных
class StreamingVTXDecoder {
private:
    FILE* vtxFile;
    VTXHeader header;
    int currentBodyPart;
    int currentModel;
    int currentLOD;
    
public:
    bool Initialize(const char* filename) {
        vtxFile = fopen(filename, "rb");
        if (!vtxFile) return false;
        
        fread(&header, sizeof(VTXHeader), 1, vtxFile);
        return ValidateHeader(header);
    }
    
    // Декодирование следующего блока данных
    bool DecodeNextChunk(GeometryChunk& outChunk) {
        if (currentBodyPart >= header.numBodyParts) {
            return false; // Конец файла
        }
        
        // Читаем и декодируем следующий chunk
        BodyPartHeader bodyPart;
        fread(&bodyPart, sizeof(BodyPartHeader), 1, vtxFile);
        
        // Декодируем strip groups для текущего body part
        DecodeStripGroups(bodyPart, outChunk);
        
        // Переходим к следующему body part
        currentBodyPart++;
        return true;
    }
};
```

### 6.2 Кэширование декомпрессированных данных

```c
// Кэш для декомпрессированной геометрии
class GeometryCache {
private:
    struct CacheEntry {
        uint32_t hash;           // Хэш исходных данных
        GeometryData* geometry;  // Декомпрессированная геометрия
        uint32_t lastAccess;     // Время последнего доступа
        uint32_t refCount;       // Счетчик ссылок
    };
    
    std::unordered_map<uint32_t, CacheEntry> cache;
    uint32_t maxCacheSize;
    uint32_t currentTime;
    
public:
    GeometryData* GetGeometry(const VTXData& vtxData) {
        uint32_t hash = CalculateHash(vtxData);
        
        auto it = cache.find(hash);
        if (it != cache.end()) {
            // Cache hit
            it->second.lastAccess = currentTime++;
            it->second.refCount++;
            return it->second.geometry;
        }
        
        // Cache miss - декомпрессируем данные
        GeometryData* geometry = DecompressVTXData(vtxData);
        
        // Добавляем в кэш
        if (cache.size() >= maxCacheSize) {
            EvictLeastRecentlyUsed();
        }
        
        CacheEntry entry;
        entry.hash = hash;
        entry.geometry = geometry;
        entry.lastAccess = currentTime++;
        entry.refCount = 1;
        
        cache[hash] = entry;
        return geometry;
    }
};
```

## 7. Оптимизации производительности

### 7.1 SIMD оптимизации

```c
// Векторизованная обработка вершин
void ProcessVerticesSIMD(Vertex* vertices, int numVertices, Matrix4x4& transform) {
    __m128 transform_row0 = _mm_load_ps(&transform.m[0][0]);
    __m128 transform_row1 = _mm_load_ps(&transform.m[1][0]);
    __m128 transform_row2 = _mm_load_ps(&transform.m[2][0]);
    __m128 transform_row3 = _mm_load_ps(&transform.m[3][0]);
    
    for (int i = 0; i < numVertices; i += 4) {
        // Загружаем 4 вершины одновременно
        __m128 pos_x = _mm_set_ps(vertices[i+3].position.x, vertices[i+2].position.x,
                                  vertices[i+1].position.x, vertices[i+0].position.x);
        __m128 pos_y = _mm_set_ps(vertices[i+3].position.y, vertices[i+2].position.y,
                                  vertices[i+1].position.y, vertices[i+0].position.y);
        __m128 pos_z = _mm_set_ps(vertices[i+3].position.z, vertices[i+2].position.z,
                                  vertices[i+1].position.z, vertices[i+0].position.z);
        __m128 pos_w = _mm_set1_ps(1.0f);
        
        // Применяем трансформацию
        __m128 result_x = _mm_add_ps(_mm_add_ps(_mm_mul_ps(pos_x, _mm_shuffle_ps(transform_row0, transform_row0, 0x00)),
                                                _mm_mul_ps(pos_y, _mm_shuffle_ps(transform_row0, transform_row0, 0x55))),
                                     _mm_add_ps(_mm_mul_ps(pos_z, _mm_shuffle_ps(transform_row0, transform_row0, 0xAA)),
                                                _mm_mul_ps(pos_w, _mm_shuffle_ps(transform_row0, transform_row0, 0xFF))));
        
        // Сохраняем результат
        float result[4];
        _mm_store_ps(result, result_x);
        
        for (int j = 0; j < 4 && i + j < numVertices; j++) {
            vertices[i + j].position.x = result[j];
        }
    }
}
```

### 7.2 Многопоточная декомпрессия

```c
// Многопоточный декодер
class ParallelVTXDecoder {
private:
    struct DecodingTask {
        VTXStripGroup* stripGroup;
        GeometryChunk* outputChunk;
        std::atomic<bool> completed;
    };
    
    std::vector<std::thread> workerThreads;
    std::queue<DecodingTask*> taskQueue;
    std::mutex queueMutex;
    std::condition_variable taskAvailable;
    bool shutdown;
    
    void WorkerThread() {
        while (!shutdown) {
            DecodingTask* task = nullptr;
            
            {
                std::unique_lock<std::mutex> lock(queueMutex);
                taskAvailable.wait(lock, [this] { return !taskQueue.empty() || shutdown; });
                
                if (shutdown) break;
                
                task = taskQueue.front();
                taskQueue.pop();
            }
            
            if (task) {
                DecodeStripGroup(*task->stripGroup, *task->outputChunk);
                task->completed = true;
            }
        }
    }
    
public:
    void Initialize(int numThreads) {
        shutdown = false;
        
        for (int i = 0; i < numThreads; i++) {
            workerThreads.emplace_back(&ParallelVTXDecoder::WorkerThread, this);
        }
    }
    
    void DecodeParallel(VTXData& vtxData, GeometryData& outputGeometry) {
        std::vector<DecodingTask> tasks;
        
        // Создаем задачи для каждой strip group
        for (auto& stripGroup : vtxData.stripGroups) {
            DecodingTask task;
            task.stripGroup = &stripGroup;
            task.outputChunk = &outputGeometry.chunks[tasks.size()];
            task.completed = false;
            
            tasks.push_back(task);
            
            {
                std::lock_guard<std::mutex> lock(queueMutex);
                taskQueue.push(&tasks.back());
            }
            taskAvailable.notify_one();
        }
        
        // Ждем завершения всех задач
        bool allCompleted = false;
        while (!allCompleted) {
            allCompleted = true;
            for (const auto& task : tasks) {
                if (!task.completed) {
                    allCompleted = false;
                    break;
                }
            }
            std::this_thread::sleep_for(std::chrono::microseconds(100));
        }
    }
};
```

## Заключение

Алгоритмы сжатия и декомпрессии в форматах моделей Valve представляют собой комплексную систему оптимизаций:

1. **Vertex Cache Optimization** обеспечивает эффективное использование аппаратного кэша GPU
2. **Triangle Strip Encoding** снижает объем данных и улучшает производительность рендеринга
3. **Bone Weight Quantization** экономит память при сохранении качества анимации
4. **LOD Progressive Meshes** обеспечивают масштабируемое качество в зависимости от расстояния
5. **Fixup Tables** позволяют плавные переходы между уровнями детализации

Эти технологии в совокупности обеспечивают высокую производительность рендеринга при сохранении качества визуализации.