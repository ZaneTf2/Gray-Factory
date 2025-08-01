# Комплексный технический анализ форматов моделей Valve Source Engine

## Обзор архитектуры

Source Engine использует трехфайловую архитектуру для хранения 3D моделей:

- **MDL** (Model) - основной файл с метаданными модели
- **VVD** (Valve Vertex Data) - данные вершин
- **VTX** (Valve Triangle eXtended) - оптимизированные индексы треугольников

## 1. MDL Format - Основной файл модели

### 1.1 Структура заголовка MDL

```c
struct studiohdr_t
{
    int id;                    // Model format ID IDST/IDSQ
    int version;               // Format version number
    long checksum;             // This has to be the same in the phy and vtx files
    char name[64];             // The internal name of the model
    int length;                // Data size of MDL file in bytes
    
    Vector eyeposition;        // Ideal eye position
    Vector illumposition;      // Illumination center
    Vector hull_min;           // Ideal movement hull size
    Vector hull_max;
    Vector view_bbmin;         // Clipping bounding box
    Vector view_bbmax;
    
    int flags;                 // Model flags
    int numbones;              // Number of bones
    int boneindex;             // Offset to first bone chunk
    
    int numbonecontrollers;    // Bone controllers
    int bonecontrollerindex;
    
    int numhitboxsets;         // Complex bounding boxes
    int hitboxsetindex;
    
    int numlocalanim;          // Animations/poses
    int localanimindex;        // Animation descriptions
    
    int numlocalseq;           // Sequences
    int localseqindex;         // Sequence descriptions
    
    int activitylistversion;   // Initialization flag
    int eventsindexed;
    
    int numtextures;           // Raw textures
    int textureindex;
    
    int numcdtextures;         // Texture directories
    int cdtextureindex;
    
    int numskinref;            // Replaceable textures tables
    int numskinfamilies;
    int skinindex;
    
    int numbodyparts;          // Bodypart index
    int bodypartindex;
    
    int numattachments;        // Queryable attachable points
    int attachmentindex;
    
    int numlocalposeparameters; // Pose parameters
    int localposeparamindex;
    
    int surfacepropindex;      // Surface property value
    
    int keyvalueindex;         // Key:value data
    int keyvaluesize;
    
    int numlocalikchains;      // IK chains
    int localikchainindex;
    
    // Additional data follows...
};
```

### 1.2 Ключевые компоненты MDL

#### Body Parts (Части тела)
```c
struct mstudiobodyparts_t
{
    int sznameindex;           // Body part name
    int nummodels;             // Number of models in this body part
    int base;                  // Base value
    int modelindex;            // Index into models array
};
```

#### Models (Модели)
```c
struct mstudiomodel_t
{
    char name[64];             // Model name
    int type;                  // Model type
    float boundingradius;      // Model bounding sphere radius
    
    int nummeshes;             // Number of meshes
    int meshindex;             // Index of first mesh
    
    int numvertices;           // Number of unique vertices/normals/texcoords
    int vertexindex;           // Vertex Vector
    int tangentsindex;         // Tangents Vector
    
    int numattachments;        // Attachments
    int attachmentindex;
    
    int numeyeballs;           // Eyeball models
    int eyeballindex;
    
    mstudio_modelvertexdata_t vertexdata; // Vertex data
    
    int unused[8];             // Remove as appropriate
};
```

#### Meshes (Меши)
```c
struct mstudiomesh_t
{
    int material;              // Material index
    int modelindex;            // Model index
    
    int numvertices;           // Number of unique vertices
    int vertexoffset;          // Vertex mstudiovertex_t
    
    int numflexes;             // Vertex animation
    int flexindex;
    
    int materialtype;          // Material type
    int materialparam;         // Material parameter
    
    int meshid;                // Mesh identifier
    
    Vector center;             // Center of mesh
    
    mstudio_meshvertexdata_t vertexdata; // Vertex data
    
    int unused[8];             // Remove as appropriate
};
```

## 2. VVD Format - Данные вершин

### 2.1 Структура заголовка VVD

```c
struct vertexFileHeader_t
{
    int id;                    // FILE_ID (IDSV)
    int version;               // FILE_VERSION
    long checksum;             // Same as studiohdr_t, ensures sync
    int numLODs;               // Number of LODs
    int numLODVertexes[MAX_NUM_LODS]; // Number of verts for desired root LOD
    int numFixups;             // Number of fixup table entries
    int fixupTableStart;       // Offset from base to fixup table
    int vertexDataStart;       // Offset from base to vertex block
    int tangentDataStart;      // Offset from base to tangent block
};
```

### 2.2 Структура вершины

```c
struct mstudiovertex_t
{
    mstudioboneweight_t m_BoneWeights; // Bone weights
    Vector m_vecPosition;              // Vertex position
    Vector m_vecNormal;                // Vertex normal
    Vector2D m_vecTexCoord;            // Texture coordinates
};

struct mstudioboneweight_t
{
    float weight[MAX_NUM_BONES_PER_VERT]; // Bone weights
    char bone[MAX_NUM_BONES_PER_VERT];    // Bone indices
    byte numbones;                        // Number of bones
};
```

### 2.3 Алгоритм загрузки VVD

1. **Чтение заголовка**: Проверка ID, версии и контрольной суммы
2. **Определение LOD**: Выбор уровня детализации
3. **Загрузка вершин**: Чтение массива структур mstudiovertex_t
4. **Обработка Fixup Table**: Коррекция данных для различных LOD
5. **Загрузка тангентов**: Дополнительные данные для нормального маппинга

## 3. VTX Format - Оптимизированные индексы

### 3.1 Структура заголовка VTX

```c
struct OptimizedModel::FileHeader_t
{
    int version;               // FILE_VERSION
    int vertCacheSize;         // Hardware vertex cache size
    unsigned short maxBonesPerStrip; // Maximum bones per triangle strip
    unsigned short maxBonesPerTri;   // Maximum bones per triangle
    int maxBonesPerVert;       // Maximum bones per vertex
    long checkSum;             // Same as studiohdr_t
    int numLODs;               // Number of LODs
    int materialReplacementListOffset; // Offset to material replacement list
    int numBodyParts;          // Number of body parts
    int bodyPartOffset;        // Offset to body part array
};
```

### 3.2 Иерархия структур VTX

#### Body Parts
```c
struct BodyPartHeader_t
{
    int numModels;             // Number of models
    int modelOffset;           // Offset to model array
};
```

#### Models
```c
struct ModelHeader_t
{
    int numLODs;               // Number of LODs
    int lodOffset;             // Offset to LOD array
};
```

#### LODs (Level of Detail)
```c
struct ModelLODHeader_t
{
    int numMeshes;             // Number of meshes
    int meshOffset;            // Offset to mesh array
    float switchPoint;         // LOD switch distance
};
```

#### Meshes
```c
struct MeshHeader_t
{
    int numStripGroups;        // Number of strip groups
    int stripGroupHeaderOffset; // Offset to strip group array
    unsigned char flags;       // Mesh flags
};
```

#### Strip Groups
```c
struct StripGroupHeader_t
{
    int numVerts;              // Number of vertices
    int vertOffset;            // Offset to vertex array
    
    int numIndices;            // Number of indices
    int indexOffset;           // Offset to index array
    
    int numStrips;             // Number of strips
    int stripOffset;           // Offset to strip array
    
    unsigned char flags;       // Strip group flags
};
```

#### Optimized Vertex
```c
struct Vertex_t
{
    unsigned char boneWeightIndex[3]; // Bone weight indices
    unsigned char numBones;           // Number of bones
    
    unsigned short origMeshVertID;    // Original mesh vertex index
    
    char boneID[3];                   // Bone IDs
};
```

#### Strip
```c
struct StripHeader_t
{
    int numIndices;            // Number of indices in strip
    int indexOffset;           // Offset to index array
    
    int numVerts;              // Number of vertices
    int vertOffset;            // Offset to vertex array
    
    short numBones;            // Number of bones
    unsigned char flags;       // Strip flags
    
    int numBoneStateChanges;   // Number of bone state changes
    int boneStateChangeOffset; // Offset to bone state change array
};
```

## 4. Алгоритмы парсинга и загрузки

### 4.1 Последовательность загрузки модели

```python
def load_source_model(mdl_path):
    # 1. Загрузка MDL файла
    mdl_data = parse_mdl_file(mdl_path)
    
    # 2. Проверка контрольных сумм
    vvd_path = mdl_path.replace('.mdl', '.vvd')
    vtx_path = mdl_path.replace('.mdl', '.dx90.vtx')
    
    vvd_data = parse_vvd_file(vvd_path)
    vtx_data = parse_vtx_file(vtx_path)
    
    if not validate_checksums(mdl_data, vvd_data, vtx_data):
        raise ValueError("Checksum mismatch between model files")
    
    # 3. Построение геометрии
    geometry = build_geometry(mdl_data, vvd_data, vtx_data)
    
    return geometry
```

### 4.2 Алгоритм построения геометрии

```python
def build_geometry(mdl_data, vvd_data, vtx_data):
    vertices = []
    indices = []
    
    # Итерация по body parts
    for bp_idx, bodypart in enumerate(vtx_data.bodyparts):
        # Итерация по моделям в body part
        for model_idx, model in enumerate(bodypart.models):
            # Выбираем LOD 0 (максимальная детализация)
            lod = model.lods[0]
            
            # Итерация по мешам
            for mesh_idx, mesh in enumerate(lod.meshes):
                # Итерация по strip groups
                for sg_idx, strip_group in enumerate(mesh.strip_groups):
                    # Обработка vertex remapping
                    vertex_remap = []
                    for vert in strip_group.vertices:
                        vertex_remap.append(vert.origMeshVertID)
                    
                    # Обработка triangle strips
                    for strip in strip_group.strips:
                        strip_indices = []
                        for i in range(strip.numIndices):
                            local_idx = strip.indices[i]
                            global_idx = vertex_remap[local_idx]
                            strip_indices.append(global_idx)
                        
                        # Конвертация triangle strip в треугольники
                        triangles = convert_strip_to_triangles(strip_indices)
                        indices.extend(triangles)
    
    # Загрузка вершин из VVD
    for i in range(vvd_data.numLODVertexes[0]):
        vertex = vvd_data.vertices[i]
        vertices.append({
            'position': vertex.position,
            'normal': vertex.normal,
            'texcoord': vertex.texcoord,
            'bone_weights': vertex.bone_weights,
            'bone_indices': vertex.bone_indices
        })
    
    return {
        'vertices': vertices,
        'indices': indices
    }
```

### 4.3 Конвертация Triangle Strips

```python
def convert_strip_to_triangles(strip_indices):
    """
    Конвертирует triangle strip в список треугольников
    с правильной ориентацией нормалей
    """
    triangles = []
    
    if len(strip_indices) < 3:
        return triangles
    
    for i in range(len(strip_indices) - 2):
        idx1 = strip_indices[i]
        idx2 = strip_indices[i + 1]
        idx3 = strip_indices[i + 2]
        
        # Пропускаем вырожденные треугольники
        if idx1 == idx2 or idx2 == idx3 or idx1 == idx3:
            continue
        
        # Чередуем порядок вершин для правильной ориентации
        if i % 2 == 0:
            # Четный треугольник - нормальный порядок
            triangles.extend([idx1, idx2, idx3])
        else:
            # Нечетный треугольник - обратный порядок
            triangles.extend([idx1, idx3, idx2])
    
    return triangles
```

## 5. Оптимизации и особенности

### 5.1 Vertex Cache Optimization

VTX файлы оптимизированы для аппаратного кэша вершин:

- **Vertex Cache Size**: Размер кэша вершин GPU (обычно 16-32)
- **Strip Organization**: Треугольники организованы в strips для минимизации cache miss
- **Bone Limitations**: Ограничения на количество костей на strip/треугольник/вершину

### 5.2 LOD System

Система уровней детализации:

- **LOD 0**: Максимальная детализация (все вершины)
- **LOD 1-7**: Упрощенные версии с меньшим количеством вершин
- **Switch Points**: Расстояния переключения между LOD

### 5.3 Bone Weighting

Система скелетной анимации:

- **Максимум 3 кости на вершину** в большинстве случаев
- **Нормализованные веса** (сумма = 1.0)
- **Bone State Changes**: Оптимизация переключений костей в strips

## 6. Практические рекомендации

### 6.1 Валидация данных

```python
def validate_model_data(mdl_data, vvd_data, vtx_data):
    # Проверка контрольных сумм
    if mdl_data.checksum != vvd_data.checksum != vtx_data.checksum:
        return False
    
    # Проверка версий
    if mdl_data.version < MIN_SUPPORTED_VERSION:
        return False
    
    # Проверка соответствия количества body parts
    if mdl_data.numbodyparts != vtx_data.numBodyParts:
        return False
    
    return True
```

### 6.2 Обработка ошибок

```python
def safe_parse_vtx(file_path):
    try:
        with open(file_path, 'rb') as f:
            header = parse_vtx_header(f)
            
            # Валидация заголовка
            if header.version != EXPECTED_VTX_VERSION:
                raise ValueError(f"Unsupported VTX version: {header.version}")
            
            # Парсинг данных с проверками
            data = parse_vtx_data(f, header)
            return data
            
    except struct.error as e:
        raise ValueError(f"VTX file corrupted: {e}")
    except IOError as e:
        raise ValueError(f"Cannot read VTX file: {e}")
```

### 6.3 Оптимизация производительности

- **Кэширование**: Сохранение обработанных данных
- **Потоковая загрузка**: Асинхронная загрузка файлов
- **Память**: Освобождение неиспользуемых LOD
- **GPU Upload**: Оптимизация передачи данных на GPU

## 7. Заключение

Архитектура форматов моделей Source Engine представляет собой высокооптимизированную систему для эффективного хранения и загрузки 3D моделей. Трехфайловая структура обеспечивает:

- **Модульность**: Разделение метаданных, вершин и индексов
- **Оптимизацию**: Специализированные структуры для GPU
- **Масштабируемость**: Поддержка LOD и различных уровней качества
- **Совместимость**: Контрольные суммы для синхронизации файлов

Правильная реализация парсеров требует глубокого понимания всех трех форматов и их взаимосвязей.