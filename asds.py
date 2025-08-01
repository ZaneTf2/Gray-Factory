class Vector3:
    def __init__(self, x=0, y=0, z=0):
        self.x, self.y, self.z = x, y, z
    
    def __repr__(self):
        return f"Vector3({self.x:.3f}, {self.y:.3f}, {self.z:.3f})"
    
    def normalize(self):
        length = (self.x**2 + self.y**2 + self.z**2)**0.5
        if length > 0:
            self.x /= length
            self.y /= length
            self.z /= length
        return self

class MDLTexture:
    """Структура текстуры MDL"""
    def __init__(self):
        self.name_offset = 0
        self.flags = 0
        self.used = 0
        self.unused = 0
        self.name = ""

class MDLBodyPart:
    """Структура части тела модели"""
    def __init__(self):
        self.name_offset = 0
        self.nummodels = 0
        self.base = 0
        self.modelindex = 0
        self.name = ""

class MDLModel:
    """Структура модели внутри части тела"""
    def __init__(self):
        self.name = ""
        self.type = 0
        self.boundingradius = 0.0
        self.nummeshes = 0
        self.meshindex = 0
        self.numvertices = 0
        self.vertexindex = 0
        self.tangentsindex = 0

class MDLMesh:
    """Структура меша модели"""
    def __init__(self):
        self.material = 0
        self.modelindex = 0
        self.numvertices = 0
        self.vertexoffset = 0
        self.numflexes = 0
        self.flexindex = 0
        self.materialtype = 0
        self.materialparam = 0
        self.meshid = 0
        self.center = Vector3()

class MDLHeader:
    def __init__(self):
        self.id = 0
        self.version = 0
        self.checksum = 0
        self.name = ""
        self.dataLength = 0
        self.eyeposition = Vector3()
        self.illumposition = Vector3()
        self.hull_min = Vector3()
        self.hull_max = Vector3()
        self.view_bbmin = Vector3()
        self.view_bbmax = Vector3()
        self.flags = 0
        self.bone_count = 0
        self.bone_offset = 0
        self.texture_count = 0
        self.texture_offset = 0

class VVDHeader:
    """Заголовок VVD файла"""
    def __init__(self):
        self.id = 0                    # "IDSV"
        self.version = 0
        self.checksum = 0
        self.numLODs = 0
        self.numLODVertexes = []
        self.numFixups = 0
        self.fixupTableStart = 0
        self.vertexDataStart = 0
        self.tangentDataStart = 0

class Vertex:
    """Структура вершины"""
    def __init__(self):
        self.m_BoneWeights = [0.0] * 3
        self.m_BoneIndices = [0] * 3
        self.m_vecPosition = Vector3()
        self.m_vecNormal = Vector3()
        self.m_vecTexCoord = [0.0, 0.0]

class Vector3:
    def __init__(self, x=0, y=0, z=0):
        self.x = x
        self.y = y
        self.z = z

class MDLHeader:
    def __init__(self):
        self.id = 0
        self.version = 0
        self.checksum = 0
        self.name = ""
        self.length = 0
        self.eyeposition = Vector3()
        self.illumposition = Vector3()
        self.hull_min = Vector3()
        self.hull_max = Vector3()
        self.view_bbmin = Vector3()
        self.view_bbmax = Vector3()
        self.flags = 0
        self.bone_count = 0
        self.bone_offset = 0
        self.bonecontroller_count = 0
        self.bonecontroller_offset = 0
        self.hitbox_count = 0
        self.hitbox_offset = 0
        self.sequence_count = 0
        self.sequence_offset = 0
        self.texture_count = 0
        self.texture_offset = 0
        self.bodypart_count = 0
        self.bodypart_offset = 0

class ImprovedMDLLoader:
    def __init__(self, scale=1.0):
        self.header = None
        self.vertices = []  # Будет содержать координаты [x,y,z, x,y,z, ...]
        self.vertex_positions = []  # Временное хранение для загрузки
        self.indices = []
        self.textures = []
        self.bodyparts = []
        self.models = []
        self.meshes = []
        self.debug_info = {}
        self.scale = scale  # Масштаб модели
        
    def _parse_model(self, f):
        """Читает данные модели из MDL файла"""
        name = f.read(64).decode('ascii', errors='ignore').rstrip('\x00')
        type = struct.unpack('I', f.read(4))[0]
        boundingradius = struct.unpack('f', f.read(4))[0]
        mesh_count = struct.unpack('I', f.read(4))[0]
        mesh_offset = struct.unpack('I', f.read(4))[0]
        
        # Проверяем валидность данных
        if mesh_count > 1024:  # Разумное ограничение на количество мешей
            print(f"[Model Viewer] Warning: Unusually high mesh count: {mesh_count}, truncating")
            mesh_count = min(mesh_count, 1024)
        
        vertex_count = struct.unpack('I', f.read(4))[0]
        vertex_offset = struct.unpack('I', f.read(4))[0]
        tangent_offset = struct.unpack('I', f.read(4))[0]
        
        attachment_count = struct.unpack('I', f.read(4))[0]
        attachment_offset = struct.unpack('I', f.read(4))[0]
        
        eyeball_count = struct.unpack('I', f.read(4))[0]
        eyeball_offset = struct.unpack('I', f.read(4))[0]
        
        model = {
            'name': name,
            'type': type,
            'boundingradius': boundingradius,
            'mesh_count': mesh_count,
            'mesh_offset': mesh_offset,
            'vertex_count': vertex_count,
            'vertex_offset': vertex_offset,
            'meshes': []
        }
        
        # Сохраняем текущую позицию
        current_pos = f.tell()
        
        # Читаем меши модели
        f.seek(mesh_offset)
        for i in range(mesh_count):
            material_index = struct.unpack('I', f.read(4))[0]
            model_offset = struct.unpack('I', f.read(4))[0]
            vertex_count = struct.unpack('I', f.read(4))[0]
            vertex_offset = struct.unpack('I', f.read(4))[0]
            flex_count = struct.unpack('I', f.read(4))[0]
            flex_offset = struct.unpack('I', f.read(4))[0]
            material_type = struct.unpack('I', f.read(4))[0]
            material_param = struct.unpack('I', f.read(4))[0]
            
            model['meshes'].append({
                'material_index': material_index,
                'model_offset': model_offset,
                'vertex_count': vertex_count,
                'vertex_offset': vertex_offset
            })
            
        # Восстанавливаем позицию
        f.seek(current_pos)
        
        return model
        
    def set_scale(self, scale):
        """Устанавливает новый масштаб модели и пересчитывает геометрию"""
        self.scale = scale
        
        # Если модель уже загружена, пересчитываем вершины
        if self.vertices:
            # Пересчитываем каждую вершину
            for i in range(0, len(self.vertices), 3):
                self.vertices[i] *= scale
                self.vertices[i+1] *= scale
                self.vertices[i+2] *= scale
                
        # Если используется bounding box, пересоздаем его
        if self.header and not self.vertices:
            self._create_bounding_box()
            
    def _parse_bones(self, f):
        """Читает кости модели"""
        if not self.header or not hasattr(self.header, 'bone_offset'):
            return
            
        f.seek(self.header.bone_offset)
        self.bones = []
        
        for i in range(self.header.bone_count):
            bone = {
                'name': f.read(32).decode('ascii', errors='ignore').rstrip('\x00'),
                'parent': struct.unpack('i', f.read(4))[0],
                'bone_controller': struct.unpack('iiiiii', f.read(24)),
                'pos': struct.unpack('fff', f.read(12)),
                'quat': struct.unpack('ffff', f.read(16)),
                'rot': struct.unpack('fff', f.read(12)),
                'pos_scale': struct.unpack('fff', f.read(12)),
                'rot_scale': struct.unpack('fff', f.read(12)),
                'pose_to_bone': [struct.unpack('ffff', f.read(16)) for _ in range(3)],
                'q_alignment': struct.unpack('ffff', f.read(16)),
                'flags': struct.unpack('i', f.read(4))[0],
                'proc_type': struct.unpack('i', f.read(4))[0],
                'proc_index': struct.unpack('i', f.read(4))[0],
                'physics_bone': struct.unpack('i', f.read(4))[0],
            }
            self.bones.append(bone)


    def load_mdl(self, filepath):
        """Загружает MDL файл"""
        try:
            # Читаем MDL файл
            with open(filepath, 'rb') as f:
                # Проверяем сигнатуру
                signature = f.read(4)
                if signature != b'IDST':
                    print("[Model Viewer] Invalid MDL signature")
                    return False
                
                # Читаем заголовок
                f.seek(0)
                self.header = self._parse_mdl_header(f)
                
                if not self._validate_header():
                    return False
                
                # Парсим компоненты модели
                self._parse_textures(f)
                self._parse_bodyparts(f)
            
            # Загружаем VVD файл
            vvd_path = os.path.splitext(filepath)[0] + ".vvd"
            if os.path.exists(vvd_path):
                if not self.load_vvd(vvd_path):
                    print("[Model Viewer] Failed to load VVD file")
                    self._create_bounding_box()
                else:
                    print("[Model Viewer] VVD file loaded successfully")
            else:
                print("[Model Viewer] VVD file not found") 
                self._create_bounding_box()

            # Выводим информацию
            vertex_count = len(self.vertices) // 3
            print(f"[Model Viewer] Model loaded:")
            print(f"  Name: {self.header.name if hasattr(self.header, 'name') else 'Unknown'}")
            print(f"  Version: {self.header.version if hasattr(self.header, 'version') else 'Unknown'}")
            print(f"  Vertices: {vertex_count}")
            print(f"  Textures: {len(self.textures)}")
            print(f"  Body parts: {len(self.bodyparts)}")
            return True

        except Exception as ex:
            print(f"[Model Viewer] Error loading MDL: {str(ex)}")
            import traceback
            traceback.print_exc()
            return False


    def _create_bounding_box(self):
        """Создает геометрию ограничивающего бокса на основе размеров модели"""
        # Используем размеры из заголовка MDL с учетом масштаба
        min_x = self.header.hull_min.x * self.scale
        min_y = self.header.hull_min.y * self.scale
        min_z = self.header.hull_min.z * self.scale
        max_x = self.header.hull_max.x * self.scale
        max_y = self.header.hull_max.y * self.scale
        max_z = self.header.hull_max.z * self.scale
        
        # Создаем вершины box'а
        self.vertices = [
            min_x, min_y, min_z,  max_x, min_y, min_z,  max_x, max_y, min_z,  min_x, max_y, min_z,
            min_x, min_y, max_z,  max_x, min_y, max_z,  max_x, max_y, max_z,  min_x, max_y, max_z,
        ]
        
        # Индексы для отрисовки граней бокса
        self.indices = [
            0, 1, 2, 2, 3, 0,  # front
            1, 5, 6, 6, 2, 1,  # right
            5, 4, 7, 7, 6, 5,  # back
            4, 0, 3, 3, 7, 4,  # left
            3, 2, 6, 6, 7, 3,  # top
            4, 5, 1, 1, 0, 4,  # bottom
        ]

    def load_vvd(self, filepath):
        """Загрузка данных вершин из VVD файла"""
        try:
            with open(filepath, 'rb') as f:
                # Проверяем сигнатуру
                signature = f.read(4)
                if signature != b'IDSV':
                    print(f"[Model Viewer] Invalid VVD signature: {signature}")
                    return False
                    
                # Читаем заголовок VVD
                f.seek(0)
                vvd_header = self._parse_vvd_header(f)
                
                # Выводим информацию о VVD файле
                print(f"[Model Viewer] VVD Header Info:")
                print(f"  Version: {vvd_header.version}")
                print(f"  Checksum: {vvd_header.checksum}")
                print(f"  LOD Count: {vvd_header.numLODs}")
                print(f"  Vertex Count (LOD0): {vvd_header.numLODVertexes[0]}")
                print(f"  Vertex Data Start: {vvd_header.vertexDataStart}")
                
                # Если контрольные суммы не совпадают, это может быть неправильный файл
                if vvd_header.checksum != self.header.checksum:
                    print(f"[Model Viewer] Warning: VVD checksum mismatch")
                    print(f"  VVD Checksum: {vvd_header.checksum}")
                    print(f"  MDL Checksum: {self.header.checksum}")
                
                # Читаем вершины
                self._parse_vertices(f, vvd_header)
                
                print(f"[Model Viewer] Loaded {len(self.vertices)//3} vertices from VVD")
                return True
                
        except Exception as e:
            print(f"[Model Viewer] Error loading VVD: {e}")
            import traceback
            traceback.print_exc()
            return False
        
    def _convert_vertices(self):
        """Конвертирует загруженные вершины в правильный формат с учетом масштаба"""
        try:
            if not self.vertex_positions:
                print("[Model Viewer] Warning: No vertices to convert")
                return

            self.vertices = []
            for vertex in self.vertex_positions:
                # Проверяем что vertex и его позиция существуют
                if hasattr(vertex, 'm_vecPosition'):
                    # Добавляем координаты X, Y, Z с учетом масштаба
                    self.vertices.extend([
                        vertex.m_vecPosition.x * self.scale,
                        vertex.m_vecPosition.y * self.scale,
                        vertex.m_vecPosition.z * self.scale
                    ])
                else:
                    print(f"[Model Viewer] Warning: Invalid vertex format")

            # Сохраняем копию исходных данных перед очисткой
            self._original_vertices = self.vertex_positions.copy()
            self.vertex_positions.clear()
            
            print(f"[Model Viewer] Converted {len(self.vertices) // 3} vertices")
        except Exception as e:
            print(f"[Model Viewer] Error converting vertices: {str(e)}")
            self.vertices = []
        
    def _parse_vvd_header(self, f):
        """Парсинг заголовка VVD файла"""
        header = VVDHeader()
        header.id = struct.unpack('I', f.read(4))[0]
        header.version = struct.unpack('I', f.read(4))[0]
        header.checksum = struct.unpack('I', f.read(4))[0]
        header.numLODs = struct.unpack('I', f.read(4))[0]
        header.numLODVertexes = [struct.unpack('I', f.read(4))[0] for _ in range(8)]  # Максимум 8 LOD
        header.numFixups = struct.unpack('I', f.read(4))[0]
        header.fixupTableStart = struct.unpack('I', f.read(4))[0]
        header.vertexDataStart = struct.unpack('I', f.read(4))[0]
        header.tangentDataStart = struct.unpack('I', f.read(4))[0]
        return header
        
    def _parse_vertices(self, f, vvd_header):
        """Парсинг данных вершин из VVD файла с учетом мешей"""
        # Сначала загружаем все вершины из VVD
        f.seek(vvd_header.vertexDataStart)
        
        # Очищаем старые данные
        self.vertices = []
        self.indices = []
        
        # Читаем вершины для LOD0 (самый детальный уровень)
        num_vertices = vvd_header.numLODVertexes[0]
        
        # В Source Engine вершина содержит:
        # - boneWeight[3] (12 bytes)
        # - boneIndex[3] (3 bytes)
        # - 1 byte padding
        # - position (12 bytes)
        # - normal (12 bytes)
        # - texcoord (8 bytes)
        vertex_size = 48  # Общий размер вершины в байтах
        vertex_positions = []  # Временное хранилище позиций вершин
        vertex_bones = []     # Веса и индексы костей
        vertex_normals = []   # Нормали
        vertex_texcoords = [] # Текстурные координаты
        
        # Читаем данные вершин
        for i in range(num_vertices):
            try:
                # Читаем блок данных для вершины целиком
                vertex_data = f.read(48)  # 48 байт - размер структуры вершины
                if len(vertex_data) < 48:
                    print(f"[Model Viewer] Warning: Unexpected end of VVD data at vertex {i}")
                    break

                # Распаковываем данные
                bone_weights = struct.unpack('fff', vertex_data[0:12])
                bone_indices = struct.unpack('BBB', vertex_data[12:15])
                # padding байт находится в vertex_data[15]
                position = struct.unpack('fff', vertex_data[16:28])
                normal = struct.unpack('fff', vertex_data[28:40])
                texcoord = struct.unpack('ff', vertex_data[40:48])
                
                # Создаем объект вершины и добавляем его в vertex_positions
                vertex = Vertex()
                vertex.m_BoneWeights = list(bone_weights)
                vertex.m_BoneIndices = list(bone_indices)
                vertex.m_vecPosition = Vector3(*position)
                vertex.m_vecNormal = Vector3(*normal)
                vertex.m_vecTexCoord = list(texcoord)
                self.vertex_positions.append(vertex)

                # Сохраняем данные и сразу применяем масштаб
                scaled_position = (
                    position[0] * self.scale,
                    position[1] * self.scale,
                    position[2] * self.scale
                )
                
                # Добавляем данные в соответствующие списки
                vertex_positions.append(scaled_position)
                vertex_bones.append((bone_weights, bone_indices))
                vertex_normals.append(normal)
                vertex_texcoords.append(texcoord)

            except Exception as e:
                print(f"[Model Viewer] Error parsing vertex {i}: {str(e)}")
                break
            
        # Преобразуем позиции вершин в плоский список для OpenGL
        self.vertices = []
        for pos in vertex_positions:
            self.vertices.extend([pos[0], pos[1], pos[2]])
            
        # Создаем индексы для построения треугольников
        # Используем strip-подобное построение для оптимизации
        num_vertices = len(vertex_positions)
        vertex_used = set()
        
        for i in range(0, num_vertices - 2):
            # Проверяем, что вершины формируют валидный треугольник
            v1, v2, v3 = vertex_positions[i], vertex_positions[i+1], vertex_positions[i+2]
            
            # Вычисляем нормаль треугольника для проверки корректности
            edge1 = (v2[0] - v1[0], v2[1] - v1[1], v2[2] - v1[2])
            edge2 = (v3[0] - v1[0], v3[1] - v1[1], v3[2] - v1[2])
            
            # Векторное произведение для получения нормали
            normal = (
                edge1[1] * edge2[2] - edge1[2] * edge2[1],
                edge1[2] * edge2[0] - edge1[0] * edge2[2],
                edge1[0] * edge2[1] - edge1[1] * edge2[0]
            )
            
            # Проверяем длину нормали (если близка к 0, значит треугольник вырожденный)
            normal_length = (normal[0]**2 + normal[1]**2 + normal[2]**2)**0.5
            
            if normal_length > 0.0001:  # Пороговое значение для проверки вырожденных треугольников
                if i not in vertex_used:
                    self.indices.extend([i, i+1, i+2])
                    vertex_used.add(i)
                    vertex_used.add(i+1)
                    vertex_used.add(i+2)
        
        # Отладочная информация
        print(f"[Model Viewer] Created {len(self.indices) // 3} valid triangles")
        
        # Конвертируем вершины после успешного парсинга
        self._convert_vertices()
        print(f"[Model Viewer] Vertices converted successfully")

                        
    def _parse_mdl_header(self, f):
        """Правильный парсинг заголовка MDL согласно studio.h"""
        header = MDLHeader()
        
        # Основные поля
        header.id = struct.unpack('<I', f.read(4))[0]
        header.version = struct.unpack('<I', f.read(4))[0]
        header.checksum = struct.unpack('<I', f.read(4))[0]
        header.name = f.read(64).decode('ascii', errors='ignore').rstrip('\x00')
        header.dataLength = struct.unpack('<I', f.read(4))[0]
        
        # Векторы (по 12 байт каждый - 3 float)
        eye_pos = struct.unpack('<fff', f.read(12))
        header.eyeposition = Vector3(*eye_pos)
        
        illum_pos = struct.unpack('<fff', f.read(12))
        header.illumposition = Vector3(*illum_pos)
        
        hull_min = struct.unpack('<fff', f.read(12))
        header.hull_min = Vector3(*hull_min)
        
        hull_max = struct.unpack('<fff', f.read(12))
        header.hull_max = Vector3(*hull_max)
        
        view_bbmin = struct.unpack('<fff', f.read(12))
        header.view_bbmin = Vector3(*view_bbmin)
        
        view_bbmax = struct.unpack('<fff', f.read(12))
        header.view_bbmax = Vector3(*view_bbmax)
        
        header.flags = struct.unpack('<I', f.read(4))[0]
        
        # Кости
        header.bone_count = struct.unpack('<I', f.read(4))[0]
        header.bone_offset = struct.unpack('<I', f.read(4))[0]
        
        # Контроллеры костей
        header.bonecontroller_count = struct.unpack('<I', f.read(4))[0]
        header.bonecontroller_offset = struct.unpack('<I', f.read(4))[0]
        
        # Hitbox
        header.hitbox_count = struct.unpack('<I', f.read(4))[0]
        header.hitbox_offset = struct.unpack('<I', f.read(4))[0]
        
        # Анимации
        header.localanim_count = struct.unpack('<I', f.read(4))[0]
        header.localanim_offset = struct.unpack('<I', f.read(4))[0]
        
        # Последовательности
        header.localseq_count = struct.unpack('<I', f.read(4))[0]
        header.localseq_offset = struct.unpack('<I', f.read(4))[0]
        
        header.activitylistversion = struct.unpack('<I', f.read(4))[0]
        header.eventsindexed = struct.unpack('<I', f.read(4))[0]
        
        # Текстуры
        header.texture_count = struct.unpack('<I', f.read(4))[0]
        header.texture_offset = struct.unpack('<I', f.read(4))[0]
        
        header.texturedir_count = struct.unpack('<I', f.read(4))[0]
        header.texturedir_offset = struct.unpack('<I', f.read(4))[0]
        
        # Скины
        header.skinreference_count = struct.unpack('<I', f.read(4))[0]
        header.skinrfamily_count = struct.unpack('<I', f.read(4))[0]
        header.skinreference_index = struct.unpack('<I', f.read(4))[0]
        
        # Части тела
        header.bodypart_count = struct.unpack('<I', f.read(4))[0]
        header.bodypart_offset = struct.unpack('<I', f.read(4))[0]
        
        # Вложения
        header.attachment_count = struct.unpack('<I', f.read(4))[0]
        header.attachment_offset = struct.unpack('<I', f.read(4))[0]
        
        return header
        
    def _validate_header(self):
        """Проверка корректности заголовка"""
        if self.header.id != 0x54534449:  # "IDST" в little-endian
            print(f"Invalid header ID: 0x{self.header.id:08X}")
            return False
        
        if self.header.version < 44 or self.header.version > 49:
            print(f"Unsupported version: {self.header.version}")
            return False
        
        return True
        
    def _parse_textures(self, f):
        """Парсинг информации о текстурах"""
        if self.header.texture_count == 0:
            return
        
        f.seek(self.header.texture_offset)
        
        for i in range(self.header.texture_count):
            texture = MDLTexture()
            texture.name_offset = struct.unpack('<I', f.read(4))[0]
            texture.flags = struct.unpack('<I', f.read(4))[0]
            texture.used = struct.unpack('<I', f.read(4))[0]
            texture.unused = struct.unpack('<I', f.read(4))[0]
            
            # Пропускаем указатели материалов (8 байт)
            f.read(8)
            
            # Пропускаем оставшуюся часть структуры (40 байт)
            f.read(40)
            
            self.textures.append(texture)
        
        # Читаем имена текстур
        for texture in self.textures:
            if texture.name_offset > 0:
                current_pos = f.tell()
                f.seek(texture.name_offset)
                name_bytes = b''
                while True:
                    byte = f.read(1)
                    if not byte or byte == b'\x00':
                        break
                    name_bytes += byte
                texture.name = name_bytes.decode('ascii', errors='ignore')
                f.seek(current_pos)
                
    def _parse_bodyparts(self, f):
        """Парсинг частей тела модели"""
        if self.header.bodypart_count == 0:
            return
        
        f.seek(self.header.bodypart_offset)
        
        for i in range(self.header.bodypart_count):
            bodypart = MDLBodyPart()
            bodypart.name_offset = struct.unpack('<I', f.read(4))[0]
            bodypart.nummodels = struct.unpack('<I', f.read(4))[0]
            bodypart.base = struct.unpack('<I', f.read(4))[0]
            bodypart.modelindex = struct.unpack('<I', f.read(4))[0]
            
            self.bodyparts.append(bodypart)
            
            print(f"  BodyPart {i}: {bodypart.nummodels} models")
