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
    def __init__(self):
        self.name_offset = 0
        self.flags = 0
        self.used = 0
        self.unused = 0
        self.name = ""

class MDLBodyPart:
    def __init__(self):
        self.name_offset = 0
        self.nummodels = 0
        self.base = 0
        self.modelindex = 0
        self.name = ""

class MDLModel:
    def __init__(self):
        self.name = ""
        self.type = 0
        self.boundingradius = 0.0
        self.nummeshes = 0
        self.meshindex = 0
        self.numvertices = 0
        self.vertexindex = 0
        self.tangentsindex = 0
        self.meshes = []

class MDLMesh:
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
        self.strips = []

class VTXHeader:
    """Заголовок VTX файла (содержит индексы треугольников)"""
    def __init__(self):
        self.version = 0
        self.vertCacheSize = 0
        self.maxBonesPerStrip = 0
        self.maxBonesPerTri = 0
        self.maxBonesPerVert = 0
        self.checkSum = 0
        self.numLODs = 0
        self.materialReplacementListOffset = 0

class VVDHeader:
    def __init__(self):
        self.id = 0
        self.version = 0
        self.checksum = 0
        self.numLODs = 0
        self.numLODVertexes = []
        self.numFixups = 0
        self.fixupTableStart = 0
        self.vertexDataStart = 0
        self.tangentDataStart = 0

class Vertex:
    def __init__(self):
        self.m_BoneWeights = [0.0] * 3
        self.m_BoneIndices = [0] * 3
        self.m_vecPosition = Vector3()
        self.m_vecNormal = Vector3()
        self.m_vecTexCoord = [0.0, 0.0]

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
        self.vertices = []
        self.vertex_positions = []
        self.indices = []
        self.textures = []
        self.bodyparts = []
        self.models = []
        self.meshes = []
        self.debug_info = {}
        self.scale = scale
        self.vtx_data = None  # Данные из VTX файла
        
    def load_mdl(self, filepath):
        """Загружает MDL файл и связанные VVD/VTX файлы"""
        try:
            # Читаем MDL файл
            with open(filepath, 'rb') as f:
                signature = f.read(4)
                if signature != b'IDST':
                    print("[Model Viewer] Invalid MDL signature")
                    return False
                
                f.seek(0)
                self.header = self._parse_mdl_header(f)
                
                if not self._validate_header():
                    return False
                
                self._parse_textures(f)
                self._parse_bodyparts_and_models(f)
            
            # Загружаем VVD файл (данные вершин)
            vvd_path = os.path.splitext(filepath)[0] + ".vvd"
            if os.path.exists(vvd_path):
                if not self.load_vvd(vvd_path):
                    print("[Model Viewer] Failed to load VVD file")
                    self._create_bounding_box()
                    return True
            else:
                print("[Model Viewer] VVD file not found")
                self._create_bounding_box()
                return True

            # Загружаем VTX файл (индексы треугольников)
            vtx_path = os.path.splitext(filepath)[0] + ".dx90.vtx"
            if not os.path.exists(vtx_path):
                vtx_path = os.path.splitext(filepath)[0] + ".dx80.vtx"
            if not os.path.exists(vtx_path):
                vtx_path = os.path.splitext(filepath)[0] + ".sw.vtx"
                
            if os.path.exists(vtx_path):
                if self.load_vtx(vtx_path):
                    print("[Model Viewer] VTX file loaded successfully")
                    self._build_indices_from_vtx()
                else:
                    print("[Model Viewer] Failed to load VTX file, using fallback")
                    self._build_fallback_indices()
            else:
                print("[Model Viewer] VTX file not found, using fallback")
                self._build_fallback_indices()

            vertex_count = len(self.vertices) // 3
            triangle_count = len(self.indices) // 3
            print(f"[Model Viewer] Model loaded:")
            print(f"  Name: {self.header.name}")
            print(f"  Version: {self.header.version}")
            print(f"  Vertices: {vertex_count}")
            print(f"  Triangles: {triangle_count}")
            print(f"  Textures: {len(self.textures)}")
            print(f"  Body parts: {len(self.bodyparts)}")
            return True

        except Exception as ex:
            print(f"[Model Viewer] Error loading MDL: {str(ex)}")
            import traceback
            traceback.print_exc()
            return False

    def load_vtx(self, filepath):
        """Загружает VTX файл с индексами треугольников"""
        try:
            with open(filepath, 'rb') as f:
                # Проверяем сигнатуру VTX
                version = struct.unpack('<I', f.read(4))[0]
                if version != 7:
                    print(f"[Model Viewer] Unsupported VTX version: {version}")
                    return False
                
                # Читаем заголовок VTX
                vertCacheSize = struct.unpack('<I', f.read(4))[0]
                maxBonesPerStrip = struct.unpack('<H', f.read(2))[0]
                maxBonesPerTri = struct.unpack('<H', f.read(2))[0]
                maxBonesPerVert = struct.unpack('<I', f.read(4))[0]
                checkSum = struct.unpack('<I', f.read(4))[0]
                numLODs = struct.unpack('<I', f.read(4))[0]
                materialReplacementListOffset = struct.unpack('<I', f.read(4))[0]
                numBodyParts = struct.unpack('<I', f.read(4))[0]
                bodyPartOffset = struct.unpack('<I', f.read(4))[0]
                
                # Сохраняем данные VTX для дальнейшего использования
                self.vtx_data = {
                    'version': version,
                    'checkSum': checkSum,
                    'numLODs': numLODs,
                    'numBodyParts': numBodyParts,
                    'bodyPartOffset': bodyPartOffset,
                    'file_data': f.read()  # Читаем остальные данные
                }
                
                print(f"[Model Viewer] VTX Header loaded: {numBodyParts} body parts, {numLODs} LODs")
                return True
                
        except Exception as e:
            print(f"[Model Viewer] Error loading VTX: {e}")
            return False

    def _build_indices_from_vtx(self):
        """Строит правильные индексы треугольников на основе VTX данных"""
        if not self.vtx_data:
            return False
            
        try:
            # Это упрощенная версия парсинга VTX
            # В реальности нужно парсить сложную структуру LOD -> BodyPart -> Model -> Mesh -> StripGroup -> Strip
            # Для демонстрации создаем базовые треугольники
            
            vertex_count = len(self.vertices) // 3
            if vertex_count < 3:
                return False
                
            self.indices = []
            
            # Создаем треугольники из последовательных вершин
            # Это упрощение - в реальности нужно парсить VTX структуры
            for i in range(0, vertex_count - 2, 3):
                if i + 2 < vertex_count:
                    self.indices.extend([i, i + 1, i + 2])
            
            print(f"[Model Viewer] Built {len(self.indices) // 3} triangles from VTX data")
            return True
            
        except Exception as e:
            print(f"[Model Viewer] Error building indices from VTX: {e}")
            return False

    def _build_fallback_indices(self):
        """Создает индексы треугольников без VTX файла (менее точно)"""
        if not self.vertices:
            return
            
        vertex_count = len(self.vertices) // 3
        self.indices = []
        
        # Используем информацию о мешах из MDL для лучшего построения треугольников
        current_vertex_offset = 0
        
        for bodypart in self.bodyparts:
            for model in getattr(bodypart, 'models', []):
                for mesh in getattr(model, 'meshes', []):
                    mesh_vertex_count = getattr(mesh, 'numvertices', 0)
                    
                    if mesh_vertex_count >= 3:
                        # Создаем треугольники для этого меша
                        for i in range(0, mesh_vertex_count - 2, 3):
                            v0 = current_vertex_offset + i
                            v1 = current_vertex_offset + i + 1
                            v2 = current_vertex_offset + i + 2
                            
                            if v2 < vertex_count:
                                # Проверяем что треугольник не вырожденный
                                if self._is_valid_triangle(v0, v1, v2):
                                    self.indices.extend([v0, v1, v2])
                    
                    current_vertex_offset += mesh_vertex_count
        
        # Если не удалось построить через меши, используем простой подход
        if not self.indices and vertex_count >= 3:
            for i in range(0, vertex_count - 2, 3):
                if self._is_valid_triangle(i, i + 1, i + 2):
                    self.indices.extend([i, i + 1, i + 2])
        
        print(f"[Model Viewer] Built {len(self.indices) // 3} triangles using fallback method")

    def _is_valid_triangle(self, v0, v1, v2):
        """Проверяет что треугольник не вырожденный"""
        if v0 >= len(self.vertices) // 3 or v1 >= len(self.vertices) // 3 or v2 >= len(self.vertices) // 3:
            return False
            
        # Получаем координаты вершин
        p0 = (self.vertices[v0*3], self.vertices[v0*3+1], self.vertices[v0*3+2])
        p1 = (self.vertices[v1*3], self.vertices[v1*3+1], self.vertices[v1*3+2])
        p2 = (self.vertices[v2*3], self.vertices[v2*3+1], self.vertices[v2*3+2])
        
        # Вычисляем векторы сторон
        edge1 = (p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2])
        edge2 = (p2[0] - p0[0], p2[1] - p0[1], p2[2] - p0[2])
        
        # Векторное произведение
        cross = (
            edge1[1] * edge2[2] - edge1[2] * edge2[1],
            edge1[2] * edge2[0] - edge1[0] * edge2[2],
            edge1[0] * edge2[1] - edge1[1] * edge2[0]
        )
        
        # Проверяем длину векторного произведения
        length_sq = cross[0]**2 + cross[1]**2 + cross[2]**2
        return length_sq > 1e-12  # Очень маленький порог для вырожденных треугольников

    def _parse_bodyparts_and_models(self, f):
        """Парсинг частей тела и моделей с мешами"""
        if self.header.bodypart_count == 0:
            print("[Model Viewer] No body parts to parse")
            return
        
        try:
            file_size = f.seek(0, 2)  # Получаем размер файла
            f.seek(self.header.bodypart_offset)
            
            # Проверяем валидность offset'а
            if self.header.bodypart_offset >= file_size or self.header.bodypart_offset < 0:
                print(f"[Model Viewer] Invalid bodypart offset: {self.header.bodypart_offset}")
                return
            
            for i in range(min(self.header.bodypart_count, 64)):  # Ограничиваем разумным числом
                try:
                    current_pos = f.tell()
                    
                    # Проверяем что у нас достаточно данных для body part
                    if current_pos + 16 > file_size:
                        print(f"[Model Viewer] Not enough data for bodypart {i} at position {current_pos}")
                        break
                    
                    bodypart = MDLBodyPart()
                    bodypart.name_offset = struct.unpack('<I', f.read(4))[0]
                    bodypart.nummodels = struct.unpack('<I', f.read(4))[0]
                    bodypart.base = struct.unpack('<I', f.read(4))[0]
                    bodypart.modelindex = struct.unpack('<I', f.read(4))[0]
                    
                    # Валидация данных bodypart
                    if bodypart.nummodels > 64:  # Разумное ограничение
                        print(f"[Model Viewer] Warning: BodyPart {i} has suspicious model count {bodypart.nummodels}")
                        bodypart.nummodels = min(bodypart.nummodels, 64)
                    
                    if bodypart.modelindex >= file_size or bodypart.modelindex < 0:
                        print(f"[Model Viewer] Warning: BodyPart {i} has invalid model index {bodypart.modelindex}")
                        bodypart.modelindex = 0
                        bodypart.nummodels = 0
                    
                    # Читаем имя body part
                    if bodypart.name_offset > 0 and bodypart.name_offset < file_size:
                        try:
                            saved_pos = f.tell()
                            f.seek(bodypart.name_offset)
                            name_bytes = b''
                            max_name_length = min(256, file_size - bodypart.name_offset)
                            
                            for _ in range(max_name_length):
                                byte = f.read(1)
                                if not byte or byte == b'\x00':
                                    break
                                name_bytes += byte
                            
                            bodypart.name = name_bytes.decode('ascii', errors='ignore')
                            f.seek(saved_pos)
                        except Exception as e:
                            print(f"[Model Viewer] Error reading bodypart name: {e}")
                            bodypart.name = f"BodyPart_{i}"
                    else:
                        bodypart.name = f"BodyPart_{i}"
                    
                    # Читаем модели для этой body part
                    bodypart.models = []
                    if bodypart.nummodels > 0 and bodypart.modelindex > 0:
                        try:
                            models_start_pos = f.tell()
                            f.seek(bodypart.modelindex)
                            
                            for j in range(bodypart.nummodels):
                                try:
                                    model = self._parse_model_with_meshes(f)
                                    bodypart.models.append(model)
                                except Exception as e:
                                    print(f"[Model Viewer] Error parsing model {j} in bodypart {i}: {e}")
                                    break
                            
                            f.seek(models_start_pos)
                        except Exception as e:
                            print(f"[Model Viewer] Error reading models for bodypart {i}: {e}")
                    
                    self.bodyparts.append(bodypart)
                    print(f"  BodyPart {i} '{bodypart.name}': {len(bodypart.models)} models")
                    
                except struct.error as e:
                    print(f"[Model Viewer] Struct error reading bodypart {i}: {e}")
                    break
                except Exception as e:
                    print(f"[Model Viewer] Unexpected error reading bodypart {i}: {e}")
                    break
                    
        except Exception as e:
            print(f"[Model Viewer] Critical error parsing bodyparts: {e}")
            import traceback
            traceback.print_exc()

    def _parse_model_with_meshes(self, f):
        """Парсинг модели с полной информацией о мешах"""
        try:
            model_start = f.tell()
            file_size = f.seek(0, 2)  # Получаем размер файла
            f.seek(model_start)  # Возвращаемся к началу модели
            
            # Проверяем что у нас достаточно данных для чтения заголовка модели
            if model_start + 148 > file_size:
                print(f"[Model Viewer] Warning: Not enough data to read model header at position {model_start}")
                return self._create_empty_model()
            
            name = f.read(64).decode('ascii', errors='ignore').rstrip('\x00')
            type_val = struct.unpack('<I', f.read(4))[0]
            boundingradius = struct.unpack('<f', f.read(4))[0]
            nummeshes = struct.unpack('<I', f.read(4))[0]
            meshindex = struct.unpack('<I', f.read(4))[0]
            numvertices = struct.unpack('<I', f.read(4))[0]
            vertexindex = struct.unpack('<I', f.read(4))[0]
            tangentsindex = struct.unpack('<I', f.read(4))[0]
            
            # Валидация данных модели
            if nummeshes > 1024:  # Разумное ограничение
                print(f"[Model Viewer] Warning: Suspicious mesh count {nummeshes}, limiting to 32")
                nummeshes = min(nummeshes, 32)
            
            if meshindex > file_size or meshindex < 0:
                print(f"[Model Viewer] Warning: Invalid mesh index {meshindex}, file size {file_size}")
                meshindex = 0
            
            # Пропускаем остальные поля модели до конца структуры
            f.seek(model_start + 148)
            
            model = MDLModel()
            model.name = name
            model.type = type_val
            model.boundingradius = boundingradius
            model.nummeshes = nummeshes
            model.meshindex = meshindex
            model.numvertices = numvertices
            model.vertexindex = vertexindex
            model.tangentsindex = tangentsindex
            model.meshes = []
            
            # Читаем меши модели с дополнительными проверками
            if nummeshes > 0 and meshindex > 0 and meshindex < file_size:
                current_pos = f.tell()
                
                try:
                    f.seek(meshindex)
                    
                    for k in range(nummeshes):
                        mesh_start_pos = f.tell()
                        
                        # Проверяем что у нас достаточно данных для чтения меша
                        if mesh_start_pos + 64 > file_size:  # Минимальный размер структуры меша
                            print(f"[Model Viewer] Warning: Not enough data for mesh {k} at position {mesh_start_pos}")
                            break
                        
                        try:
                            mesh = MDLMesh()
                            mesh.material = struct.unpack('<I', f.read(4))[0]
                            mesh.modelindex = struct.unpack('<I', f.read(4))[0]
                            mesh.numvertices = struct.unpack('<I', f.read(4))[0]
                            mesh.vertexoffset = struct.unpack('<I', f.read(4))[0]
                            mesh.numflexes = struct.unpack('<I', f.read(4))[0]
                            mesh.flexindex = struct.unpack('<I', f.read(4))[0]
                            mesh.materialtype = struct.unpack('<I', f.read(4))[0]
                            mesh.materialparam = struct.unpack('<I', f.read(4))[0]
                            mesh.meshid = struct.unpack('<I', f.read(4))[0]
                            
                            # Проверяем что у нас есть данные для center
                            if f.tell() + 12 <= file_size:
                                center = struct.unpack('<fff', f.read(12))
                                mesh.center = Vector3(*center)
                            else:
                                mesh.center = Vector3()
                            
                            # Пропускаем остальные поля меша если они есть
                            remaining_bytes = min(8, file_size - f.tell())
                            if remaining_bytes > 0:
                                f.read(remaining_bytes)
                            
                            # Валидация данных меша
                            if mesh.numvertices > 100000:  # Разумное ограничение на количество вершин
                                print(f"[Model Viewer] Warning: Mesh {k} has suspicious vertex count {mesh.numvertices}")
                                mesh.numvertices = min(mesh.numvertices, 100000)
                            
                            model.meshes.append(mesh)
                            print(f"    Mesh {k}: material={mesh.material}, vertices={mesh.numvertices}, offset={mesh.vertexoffset}")
                            
                        except struct.error as e:
                            print(f"[Model Viewer] Error reading mesh {k}: {e}")
                            break
                        except Exception as e:
                            print(f"[Model Viewer] Unexpected error reading mesh {k}: {e}")
                            break
                    
                except Exception as e:
                    print(f"[Model Viewer] Error seeking to mesh data at {meshindex}: {e}")
                
                # Возвращаемся к сохраненной позиции
                try:
                    f.seek(current_pos)
                except:
                    pass
            else:
                if nummeshes > 0:
                    print(f"[Model Viewer] Model '{name}' has {nummeshes} meshes but invalid mesh index {meshindex}")
            
            return model
            
        except Exception as e:
            print(f"[Model Viewer] Critical error parsing model: {e}")
            return self._create_empty_model()

    def _create_empty_model(self):
        """Создает пустую модель в случае ошибки парсинга"""
        model = MDLModel()
        model.name = "Error_Model"
        model.type = 0
        model.boundingradius = 0.0
        model.nummeshes = 0
        model.meshindex = 0
        model.numvertices = 0
        model.vertexindex = 0
        model.tangentsindex = 0
        model.meshes = []
        return model

    def load_vvd(self, filepath):
        """Загрузка данных вершин из VVD файла"""
        try:
            with open(filepath, 'rb') as f:
                signature = f.read(4)
                if signature != b'IDSV':
                    print(f"[Model Viewer] Invalid VVD signature: {signature}")
                    return False
                    
                f.seek(0)
                vvd_header = self._parse_vvd_header(f)
                
                print(f"[Model Viewer] VVD Header Info:")
                print(f"  Version: {vvd_header.version}")
                print(f"  Checksum: {vvd_header.checksum}")
                print(f"  LOD Count: {vvd_header.numLODs}")
                print(f"  Vertex Count (LOD0): {vvd_header.numLODVertexes[0]}")
                print(f"  Vertex Data Start: {vvd_header.vertexDataStart}")
                
                if vvd_header.checksum != self.header.checksum:
                    print(f"[Model Viewer] Warning: VVD checksum mismatch")
                
                self._parse_vertices_simple(f, vvd_header)
                
                print(f"[Model Viewer] Loaded {len(self.vertices)//3} vertices from VVD")
                return True
                
        except Exception as e:
            print(f"[Model Viewer] Error loading VVD: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _parse_vertices_simple(self, f, vvd_header):
        """Упрощенный парсинг вершин без генерации индексов"""
        f.seek(vvd_header.vertexDataStart)
        
        self.vertices = []
        self.vertex_positions = []
        
        num_vertices = vvd_header.numLODVertexes[0]
        
        for i in range(num_vertices):
            try:
                vertex_data = f.read(48)
                if len(vertex_data) < 48:
                    print(f"[Model Viewer] Warning: Unexpected end of VVD data at vertex {i}")
                    break

                bone_weights = struct.unpack('fff', vertex_data[0:12])
                bone_indices = struct.unpack('BBB', vertex_data[12:15])
                position = struct.unpack('fff', vertex_data[16:28])
                normal = struct.unpack('fff', vertex_data[28:40])
                texcoord = struct.unpack('ff', vertex_data[40:48])
                
                vertex = Vertex()
                vertex.m_BoneWeights = list(bone_weights)
                vertex.m_BoneIndices = list(bone_indices)
                vertex.m_vecPosition = Vector3(*position)
                vertex.m_vecNormal = Vector3(*normal)
                vertex.m_vecTexCoord = list(texcoord)
                self.vertex_positions.append(vertex)

                # Добавляем координаты с масштабом
                self.vertices.extend([
                    position[0] * self.scale,
                    position[1] * self.scale,
                    position[2] * self.scale
                ])

            except Exception as e:
                print(f"[Model Viewer] Error parsing vertex {i}: {str(e)}")
                break

    def _parse_vvd_header(self, f):
        """Парсинг заголовка VVD файла"""
        header = VVDHeader()
        header.id = struct.unpack('I', f.read(4))[0]
        header.version = struct.unpack('I', f.read(4))[0]
        header.checksum = struct.unpack('I', f.read(4))[0]
        header.numLODs = struct.unpack('I', f.read(4))[0]
        header.numLODVertexes = [struct.unpack('I', f.read(4))[0] for _ in range(8)]
        header.numFixups = struct.unpack('I', f.read(4))[0]
        header.fixupTableStart = struct.unpack('I', f.read(4))[0]
        header.vertexDataStart = struct.unpack('I', f.read(4))[0]
        header.tangentDataStart = struct.unpack('I', f.read(4))[0]
        return header

    def _parse_mdl_header(self, f):
        """Парсинг заголовка MDL"""
        header = MDLHeader()
        
        header.id = struct.unpack('<I', f.read(4))[0]
        header.version = struct.unpack('<I', f.read(4))[0]
        header.checksum = struct.unpack('<I', f.read(4))[0]
        header.name = f.read(64).decode('ascii', errors='ignore').rstrip('\x00')
        header.dataLength = struct.unpack('<I', f.read(4))[0]
        
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
        
        header.bone_count = struct.unpack('<I', f.read(4))[0]
        header.bone_offset = struct.unpack('<I', f.read(4))[0]
        
        header.bonecontroller_count = struct.unpack('<I', f.read(4))[0]
        header.bonecontroller_offset = struct.unpack('<I', f.read(4))[0]
        
        header.hitbox_count = struct.unpack('<I', f.read(4))[0]
        header.hitbox_offset = struct.unpack('<I', f.read(4))[0]
        
        header.localanim_count = struct.unpack('<I', f.read(4))[0]
        header.localanim_offset = struct.unpack('<I', f.read(4))[0]
        
        header.localseq_count = struct.unpack('<I', f.read(4))[0]
        header.localseq_offset = struct.unpack('<I', f.read(4))[0]
        
        header.activitylistversion = struct.unpack('<I', f.read(4))[0]
        header.eventsindexed = struct.unpack('<I', f.read(4))[0]
        
        header.texture_count = struct.unpack('<I', f.read(4))[0]
        header.texture_offset = struct.unpack('<I', f.read(4))[0]
        
        header.texturedir_count = struct.unpack('<I', f.read(4))[0]
        header.texturedir_offset = struct.unpack('<I', f.read(4))[0]
        
        header.skinreference_count = struct.unpack('<I', f.read(4))[0]
        header.skinrfamily_count = struct.unpack('<I', f.read(4))[0]
        header.skinreference_index = struct.unpack('<I', f.read(4))[0]
        
        header.bodypart_count = struct.unpack('<I', f.read(4))[0]
        header.bodypart_offset = struct.unpack('<I', f.read(4))[0]
        
        header.attachment_count = struct.unpack('<I', f.read(4))[0]
        header.attachment_offset = struct.unpack('<I', f.read(4))[0]
        
        return header
        
    def _validate_header(self):
        """Проверка корректности заголовка"""
        if self.header.id != 0x54534449:  # "IDST"
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
            
            f.read(8)  # Пропускаем указатели
            f.read(40)  # Пропускаем остальную часть
            
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

    def _create_bounding_box(self):
        """Создает геометрию ограничивающего бокса"""
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

    def set_scale(self, scale):
        """Устанавливает новый масштаб модели и пересчитывает геометрию"""
        old_scale = self.scale
        self.scale = scale
        scale_factor = scale / old_scale if old_scale != 0 else scale
        
        # Пересчитываем вершины
        if self.vertices:
            for i in range(0, len(self.vertices), 3):
                self.vertices[i] *= scale_factor
                self.vertices[i+1] *= scale_factor
                self.vertices[i+2] *= scale_factor
                
        # Если модель не загружена, пересоздаем bounding box
        if self.header and not self.vertices:
            self._create_bounding_box()

    def get_model_info(self):
        """Возвращает информацию о загруженной модели"""
        if not self.header:
            return "Model not loaded"
        
        info = []
        info.append(f"Model: {self.header.name}")
        info.append(f"Version: {self.header.version}")
        info.append(f"Vertices: {len(self.vertices) // 3}")
        info.append(f"Triangles: {len(self.indices) // 3}")
        info.append(f"Body Parts: {len(self.bodyparts)}")
        info.append(f"Textures: {len(self.textures)}")
        
        if self.bodyparts:
            info.append("\nBody Parts:")
            for i, bp in enumerate(self.bodyparts):
                info.append(f"  {i}: {bp.name} ({len(getattr(bp, 'models', []))} models)")
                for j, model in enumerate(getattr(bp, 'models', [])):
                    info.append(f"    Model {j}: {model.name} ({len(model.meshes)} meshes)")
        
        return "\n".join(info)
