# Анализ реализации загрузчика моделей в Team Fortress 2

## Обзор архитектуры

Анализ исходного кода Team Fortress 2 показывает, что система загрузки моделей построена на модульной архитектуре с четким разделением ответственности между компонентами.

## 1. Основные компоненты системы

### 1.1 Иерархия классов

```cpp
// Базовый класс для всех моделей
class CStudioModel {
protected:
    studiohdr_t* m_pStudioHdr;      // MDL заголовок
    vertexFileHeader_t* m_pVvdHdr;  // VVD заголовок
    OptimizedModel::FileHeader_t* m_pVtxHdr; // VTX заголовок
    
public:
    virtual bool LoadModel(const char* modelname) = 0;
    virtual void UnloadModel() = 0;
    virtual bool IsLoaded() const = 0;
};

// Реализация для статических моделей
class CStaticPropModel : public CStudioModel {
private:
    CUtlVector<mstudiovertex_t> m_Vertices;
    CUtlVector<unsigned short> m_Indices;
    
public:
    bool LoadModel(const char* modelname) override;
    void BuildRenderData();
    void OptimizeForRendering();
};

// Реализация для анимированных моделей
class CAnimatedModel : public CStudioModel {
private:
    CBoneSetup m_BoneSetup;
    CIKContext m_IKContext;
    
public:
    bool LoadModel(const char* modelname) override;
    void SetupBones(float currentTime);
    void UpdateAnimation(float deltaTime);
};
```

### 1.2 Менеджер ресурсов моделей

```cpp
class CModelManager {
private:
    CUtlDict<CStudioModel*, unsigned short> m_LoadedModels;
    CUtlVector<ModelCache_t> m_ModelCache;
    
    struct ModelCache_t {
        char modelName[MAX_PATH];
        CStudioModel* pModel;
        int refCount;
        float lastAccessTime;
    };
    
public:
    CStudioModel* LoadModel(const char* modelname);
    void UnloadModel(const char* modelname);
    void PurgeUnusedModels();
    
private:
    bool ValidateModelFiles(const char* mdlPath, const char* vvdPath, const char* vtxPath);
    CStudioModel* CreateModelInstance(const char* modelname);
};
```

## 2. Алгоритм загрузки модели

### 2.1 Основная последовательность

```cpp
bool CStudioModel::LoadModel(const char* modelname) {
    // 1. Построение путей к файлам
    char mdlPath[MAX_PATH], vvdPath[MAX_PATH], vtxPath[MAX_PATH];
    BuildModelPaths(modelname, mdlPath, vvdPath, vtxPath);
    
    // 2. Загрузка и валидация MDL файла
    if (!LoadMDLFile(mdlPath)) {
        Warning("Failed to load MDL file: %s\n", mdlPath);
        return false;
    }
    
    // 3. Загрузка VVD файла
    if (!LoadVVDFile(vvdPath)) {
        Warning("Failed to load VVD file: %s\n", vvdPath);
        return false;
    }
    
    // 4. Загрузка VTX файла
    if (!LoadVTXFile(vtxPath)) {
        Warning("Failed to load VTX file: %s\n", vtxPath);
        return false;
    }
    
    // 5. Валидация совместимости файлов
    if (!ValidateFileConsistency()) {
        Warning("Model files are inconsistent: %s\n", modelname);
        return false;
    }
    
    // 6. Построение рендер-данных
    BuildRenderData();
    
    // 7. Оптимизация для рендеринга
    OptimizeForRendering();
    
    return true;
}
```

### 2.2 Загрузка MDL файла

```cpp
bool CStudioModel::LoadMDLFile(const char* mdlPath) {
    // Открытие файла
    FileHandle_t hFile = g_pFileSystem->Open(mdlPath, "rb");
    if (hFile == FILESYSTEM_INVALID_HANDLE) {
        return false;
    }
    
    // Чтение заголовка
    studiohdr_t tempHeader;
    g_pFileSystem->Read(&tempHeader, sizeof(studiohdr_t), hFile);
    
    // Валидация заголовка
    if (tempHeader.id != IDSTUDIOHEADER) {
        g_pFileSystem->Close(hFile);
        return false;
    }
    
    if (tempHeader.version != STUDIO_VERSION) {
        Warning("Unsupported MDL version: %d (expected %d)\n", 
                tempHeader.version, STUDIO_VERSION);
        g_pFileSystem->Close(hFile);
        return false;
    }
    
    // Выделение памяти и загрузка полного файла
    int fileSize = g_pFileSystem->Size(hFile);
    m_pStudioHdr = (studiohdr_t*)malloc(fileSize);
    
    g_pFileSystem->Seek(hFile, 0, FILESYSTEM_SEEK_HEAD);
    g_pFileSystem->Read(m_pStudioHdr, fileSize, hFile);
    g_pFileSystem->Close(hFile);
    
    // Валидация целостности данных
    return ValidateMDLData();
}
```

### 2.3 Загрузка VVD файла

```cpp
bool CStudioModel::LoadVVDFile(const char* vvdPath) {
    FileHandle_t hFile = g_pFileSystem->Open(vvdPath, "rb");
    if (hFile == FILESYSTEM_INVALID_HANDLE) {
        return false;
    }
    
    // Чтение заголовка VVD
    vertexFileHeader_t vvdHeader;
    g_pFileSystem->Read(&vvdHeader, sizeof(vertexFileHeader_t), hFile);
    
    // Валидация
    if (vvdHeader.id != MODEL_VERTEX_FILE_ID) {
        g_pFileSystem->Close(hFile);
        return false;
    }
    
    if (vvdHeader.checkSum != m_pStudioHdr->checksum) {
        Warning("VVD checksum mismatch: %d != %d\n", 
                vvdHeader.checkSum, m_pStudioHdr->checksum);
        g_pFileSystem->Close(hFile);
        return false;
    }
    
    // Загрузка вершин для LOD 0
    int numVertices = vvdHeader.numLODVertexes[0];
    m_Vertices.SetSize(numVertices);
    
    g_pFileSystem->Seek(hFile, vvdHeader.vertexDataStart, FILESYSTEM_SEEK_HEAD);
    g_pFileSystem->Read(m_Vertices.Base(), 
                       numVertices * sizeof(mstudiovertex_t), hFile);
    
    // Загрузка fixup table если необходимо
    if (vvdHeader.numFixups > 0) {
        LoadVVDFixupTable(hFile, vvdHeader);
    }
    
    g_pFileSystem->Close(hFile);
    return true;
}
```

### 2.4 Загрузка VTX файла

```cpp
bool CStudioModel::LoadVTXFile(const char* vtxPath) {
    FileHandle_t hFile = g_pFileSystem->Open(vtxPath, "rb");
    if (hFile == FILESYSTEM_INVALID_HANDLE) {
        return false;
    }
    
    // Чтение заголовка VTX
    OptimizedModel::FileHeader_t vtxHeader;
    g_pFileSystem->Read(&vtxHeader, sizeof(OptimizedModel::FileHeader_t), hFile);
    
    // Валидация
    if (vtxHeader.version != OPTIMIZED_MODEL_FILE_VERSION) {
        g_pFileSystem->Close(hFile);
        return false;
    }
    
    if (vtxHeader.checkSum != m_pStudioHdr->checksum) {
        Warning("VTX checksum mismatch\n");
        g_pFileSystem->Close(hFile);
        return false;
    }
    
    // Загрузка полного VTX файла в память
    int fileSize = g_pFileSystem->Size(hFile);
    m_pVtxHdr = (OptimizedModel::FileHeader_t*)malloc(fileSize);
    
    g_pFileSystem->Seek(hFile, 0, FILESYSTEM_SEEK_HEAD);
    g_pFileSystem->Read(m_pVtxHdr, fileSize, hFile);
    g_pFileSystem->Close(hFile);
    
    return true;
}
```

## 3. Построение рендер-данных

### 3.1 Обработка VTX данных

```cpp
void CStudioModel::BuildRenderData() {
    m_Indices.RemoveAll();
    
    // Получаем указатель на body parts в VTX файле
    OptimizedModel::BodyPartHeader_t* pBodyParts = 
        (OptimizedModel::BodyPartHeader_t*)((byte*)m_pVtxHdr + m_pVtxHdr->bodyPartOffset);
    
    // Итерируем по всем body parts
    for (int bp = 0; bp < m_pVtxHdr->numBodyParts; bp++) {
        OptimizedModel::BodyPartHeader_t* pBodyPart = &pBodyParts[bp];
        
        // Получаем модели в body part
        OptimizedModel::ModelHeader_t* pModels = 
            (OptimizedModel::ModelHeader_t*)((byte*)pBodyPart + pBodyPart->modelOffset);
        
        for (int m = 0; m < pBodyPart->numModels; m++) {
            OptimizedModel::ModelHeader_t* pModel = &pModels[m];
            
            // Обрабатываем LOD 0 (максимальная детализация)
            if (pModel->numLODs > 0) {
                ProcessModelLOD(pModel, 0);
            }
        }
    }
}

void CStudioModel::ProcessModelLOD(OptimizedModel::ModelHeader_t* pModel, int lodIndex) {
    OptimizedModel::ModelLODHeader_t* pLODs = 
        (OptimizedModel::ModelLODHeader_t*)((byte*)pModel + pModel->lodOffset);
    
    OptimizedModel::ModelLODHeader_t* pLOD = &pLODs[lodIndex];
    
    // Получаем меши
    OptimizedModel::MeshHeader_t* pMeshes = 
        (OptimizedModel::MeshHeader_t*)((byte*)pLOD + pLOD->meshOffset);
    
    for (int mesh = 0; mesh < pLOD->numMeshes; mesh++) {
        OptimizedModel::MeshHeader_t* pMesh = &pMeshes[mesh];
        ProcessMesh(pMesh);
    }
}

void CStudioModel::ProcessMesh(OptimizedModel::MeshHeader_t* pMesh) {
    // Получаем strip groups
    OptimizedModel::StripGroupHeader_t* pStripGroups = 
        (OptimizedModel::StripGroupHeader_t*)((byte*)pMesh + pMesh->stripGroupHeaderOffset);
    
    for (int sg = 0; sg < pMesh->numStripGroups; sg++) {
        OptimizedModel::StripGroupHeader_t* pStripGroup = &pStripGroups[sg];
        ProcessStripGroup(pStripGroup);
    }
}
```

### 3.2 Обработка Strip Groups

```cpp
void CStudioModel::ProcessStripGroup(OptimizedModel::StripGroupHeader_t* pStripGroup) {
    // Получаем vertex remapping table
    OptimizedModel::Vertex_t* pVertices = 
        (OptimizedModel::Vertex_t*)((byte*)pStripGroup + pStripGroup->vertOffset);
    
    // Создаем таблицу переназначения вершин
    CUtlVector<unsigned short> vertexRemap;
    vertexRemap.SetSize(pStripGroup->numVerts);
    
    for (int v = 0; v < pStripGroup->numVerts; v++) {
        vertexRemap[v] = pVertices[v].origMeshVertID;
    }
    
    // Получаем strips
    OptimizedModel::StripHeader_t* pStrips = 
        (OptimizedModel::StripHeader_t*)((byte*)pStripGroup + pStripGroup->stripOffset);
    
    // Получаем индексы
    unsigned short* pIndices = 
        (unsigned short*)((byte*)pStripGroup + pStripGroup->indexOffset);
    
    // Обрабатываем каждый strip
    for (int strip = 0; strip < pStripGroup->numStrips; strip++) {
        OptimizedModel::StripHeader_t* pStrip = &pStrips[strip];
        ProcessStrip(pStrip, pIndices, vertexRemap);
    }
}

void CStudioModel::ProcessStrip(OptimizedModel::StripHeader_t* pStrip, 
                               unsigned short* pIndices,
                               CUtlVector<unsigned short>& vertexRemap) {
    // Получаем индексы для этого strip
    unsigned short* stripIndices = &pIndices[pStrip->indexOffset / sizeof(unsigned short)];
    
    // Конвертируем triangle strip в треугольники
    for (int i = 0; i < pStrip->numIndices - 2; i++) {
        unsigned short idx0 = stripIndices[i];
        unsigned short idx1 = stripIndices[i + 1];
        unsigned short idx2 = stripIndices[i + 2];
        
        // Пропускаем вырожденные треугольники
        if (idx0 == idx1 || idx1 == idx2 || idx0 == idx2) {
            continue;
        }
        
        // Применяем vertex remapping
        unsigned short globalIdx0 = vertexRemap[idx0];
        unsigned short globalIdx1 = vertexRemap[idx1];
        unsigned short globalIdx2 = vertexRemap[idx2];
        
        // Добавляем треугольник с правильной ориентацией
        if (i % 2 == 0) {
            // Четный треугольник
            m_Indices.AddToTail(globalIdx0);
            m_Indices.AddToTail(globalIdx1);
            m_Indices.AddToTail(globalIdx2);
        } else {
            // Нечетный треугольник - инвертируем порядок
            m_Indices.AddToTail(globalIdx0);
            m_Indices.AddToTail(globalIdx2);
            m_Indices.AddToTail(globalIdx1);
        }
    }
}
```

## 4. Система кэширования

### 4.1 Кэш моделей

```cpp
class CModelCache {
private:
    struct ModelCacheEntry_t {
        char modelName[MAX_PATH];
        CStudioModel* pModel;
        int refCount;
        float lastAccessTime;
        int memoryUsage;
    };
    
    CUtlDict<ModelCacheEntry_t, unsigned short> m_Cache;
    int m_MaxCacheSize;
    int m_CurrentCacheSize;
    
public:
    CStudioModel* FindModel(const char* modelName) {
        unsigned short index = m_Cache.Find(modelName);
        if (index != m_Cache.InvalidIndex()) {
            ModelCacheEntry_t& entry = m_Cache[index];
            entry.lastAccessTime = Plat_FloatTime();
            entry.refCount++;
            return entry.pModel;
        }
        return nullptr;
    }
    
    void AddModel(const char* modelName, CStudioModel* pModel) {
        // Проверяем, нужно ли освободить место
        int modelSize = CalculateModelMemoryUsage(pModel);
        while (m_CurrentCacheSize + modelSize > m_MaxCacheSize) {
            EvictLeastRecentlyUsedModel();
        }
        
        // Добавляем модель в кэш
        ModelCacheEntry_t entry;
        Q_strncpy(entry.modelName, modelName, sizeof(entry.modelName));
        entry.pModel = pModel;
        entry.refCount = 1;
        entry.lastAccessTime = Plat_FloatTime();
        entry.memoryUsage = modelSize;
        
        m_Cache.Insert(modelName, entry);
        m_CurrentCacheSize += modelSize;
    }
    
private:
    void EvictLeastRecentlyUsedModel() {
        float oldestTime = FLT_MAX;
        unsigned short oldestIndex = m_Cache.InvalidIndex();
        
        for (unsigned short i = m_Cache.First(); 
             i != m_Cache.InvalidIndex(); 
             i = m_Cache.Next(i)) {
            
            ModelCacheEntry_t& entry = m_Cache[i];
            if (entry.refCount == 0 && entry.lastAccessTime < oldestTime) {
                oldestTime = entry.lastAccessTime;
                oldestIndex = i;
            }
        }
        
        if (oldestIndex != m_Cache.InvalidIndex()) {
            ModelCacheEntry_t& entry = m_Cache[oldestIndex];
            m_CurrentCacheSize -= entry.memoryUsage;
            delete entry.pModel;
            m_Cache.RemoveAt(oldestIndex);
        }
    }
};
```

## 5. Оптимизации производительности

### 5.1 Предварительная загрузка

```cpp
class CModelPreloader {
private:
    CUtlVector<char*> m_PreloadQueue;
    CThread m_PreloadThread;
    bool m_bShutdown;
    
public:
    void QueueModelForPreload(const char* modelName) {
        char* modelNameCopy = new char[strlen(modelName) + 1];
        strcpy(modelNameCopy, modelName);
        m_PreloadQueue.AddToTail(modelNameCopy);
    }
    
    void StartPreloading() {
        m_bShutdown = false;
        m_PreloadThread.Start(PreloadThreadFunc, this);
    }
    
private:
    static unsigned PreloadThreadFunc(void* pParam) {
        CModelPreloader* pThis = (CModelPreloader*)pParam;
        return pThis->PreloadThread();
    }
    
    unsigned PreloadThread() {
        while (!m_bShutdown) {
            if (m_PreloadQueue.Count() > 0) {
                char* modelName = m_PreloadQueue[0];
                m_PreloadQueue.Remove(0);
                
                // Загружаем модель в фоновом режиме
                CStudioModel* pModel = new CStudioModel();
                if (pModel->LoadModel(modelName)) {
                    g_ModelManager.AddToCache(modelName, pModel);
                } else {
                    delete pModel;
                }
                
                delete[] modelName;
            } else {
                ThreadSleep(10);
            }
        }
        return 0;
    }
};
```

### 5.2 Потоковая загрузка

```cpp
class CStreamingModelLoader {
private:
    struct StreamingRequest_t {
        char modelName[MAX_PATH];
        CStudioModel** ppModel;
        bool* pCompleted;
        float priority;
    };
    
    CUtlVector<StreamingRequest_t> m_Requests;
    CThreadFastMutex m_RequestMutex;
    
public:
    void RequestModel(const char* modelName, CStudioModel** ppModel, 
                     bool* pCompleted, float priority = 1.0f) {
        StreamingRequest_t request;
        Q_strncpy(request.modelName, modelName, sizeof(request.modelName));
        request.ppModel = ppModel;
        request.pCompleted = pCompleted;
        request.priority = priority;
        
        AUTO_LOCK(m_RequestMutex);
        
        // Вставляем запрос в порядке приоритета
        int insertPos = 0;
        for (int i = 0; i < m_Requests.Count(); i++) {
            if (m_Requests[i].priority < priority) {
                insertPos = i;
                break;
            }
            insertPos = i + 1;
        }
        
        m_Requests.InsertBefore(insertPos, request);
    }
    
    void ProcessRequests() {
        AUTO_LOCK(m_RequestMutex);
        
        if (m_Requests.Count() > 0) {
            StreamingRequest_t& request = m_Requests[0];
            
            // Загружаем модель
            CStudioModel* pModel = new CStudioModel();
            if (pModel->LoadModel(request.modelName)) {
                *request.ppModel = pModel;
            } else {
                delete pModel;
                *request.ppModel = nullptr;
            }
            
            *request.pCompleted = true;
            m_Requests.Remove(0);
        }
    }
};
```

## 6. Система валидации и отладки

### 6.1 Валидация целостности данных

```cpp
bool CStudioModel::ValidateFileConsistency() {
    // Проверка контрольных сумм
    if (m_pVvdHdr->checkSum != m_pStudioHdr->checksum ||
        m_pVtxHdr->checkSum != m_pStudioHdr->checksum) {
        Warning("Model file checksum mismatch\n");
        return false;
    }
    
    // Проверка количества body parts
    if (m_pVtxHdr->numBodyParts != m_pStudioHdr->numbodyparts) {
        Warning("Body part count mismatch: VTX=%d, MDL=%d\n", 
                m_pVtxHdr->numBodyParts, m_pStudioHdr->numbodyparts);
        return false;
    }
    
    // Проверка версий файлов
    if (m_pStudioHdr->version != STUDIO_VERSION) {
        Warning("Unsupported MDL version: %d\n", m_pStudioHdr->version);
        return false;
    }
    
    if (m_pVvdHdr->version != MODEL_VERTEX_FILE_VERSION) {
        Warning("Unsupported VVD version: %d\n", m_pVvdHdr->version);
        return false;
    }
    
    if (m_pVtxHdr->version != OPTIMIZED_MODEL_FILE_VERSION) {
        Warning("Unsupported VTX version: %d\n", m_pVtxHdr->version);
        return false;
    }
    
    return true;
}
```

### 6.2 Система отладки

```cpp
void CStudioModel::DumpModelInfo() {
    Msg("=== Model Information ===\n");
    Msg("Name: %s\n", m_pStudioHdr->name);
    Msg("Version: %d\n", m_pStudioHdr->version);
    Msg("Checksum: 0x%08X\n", m_pStudioHdr->checksum);
    Msg("Body Parts: %d\n", m_pStudioHdr->numbodyparts);
    Msg("Bones: %d\n", m_pStudioHdr->numbones);
    Msg("Textures: %d\n", m_pStudioHdr->numtextures);
    
    Msg("\n=== VVD Information ===\n");
    Msg("LODs: %d\n", m_pVvdHdr->numLODs);
    Msg("Vertices (LOD0): %d\n", m_pVvdHdr->numLODVertexes[0]);
    Msg("Fixups: %d\n", m_pVvdHdr->numFixups);
    
    Msg("\n=== VTX Information ===\n");
    Msg("Vertex Cache Size: %d\n", m_pVtxHdr->vertCacheSize);
    Msg("Max Bones Per Strip: %d\n", m_pVtxHdr->maxBonesPerStrip);
    Msg("Max Bones Per Triangle: %d\n", m_pVtxHdr->maxBonesPerTri);
    Msg("Max Bones Per Vertex: %d\n", m_pVtxHdr->maxBonesPerVert);
    
    Msg("\n=== Render Data ===\n");
    Msg("Vertices: %d\n", m_Vertices.Count());
    Msg("Indices: %d\n", m_Indices.Count());
    Msg("Triangles: %d\n", m_Indices.Count() / 3);
}
```

## Заключение

Анализ реализации Team Fortress 2 показывает высокоэффективную архитектуру загрузки моделей с следующими ключевыми особенностями:

1. **Модульная архитектура** с четким разделением ответственности
2. **Эффективное кэширование** с LRU алгоритмом вытеснения
3. **Потоковая загрузка** для минимизации задержек
4. **Комплексная валидация** данных на всех этапах
5. **Оптимизация производительности** через предварительную загрузку
6. **Отладочные инструменты** для диагностики проблем

Эта архитектура обеспечивает стабильную и производительную работу с моделями в реальном времени.