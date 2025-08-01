"""
Team Fortress 2 Items Parser

This module provides functionality to parse and work with TF2 items_game.txt file.
It allows loading items data, converting it to JSON format and filtering items by various criteria.
"""
import os
import json
from pathlib import Path
import re
from typing import Dict, List, Optional, Any, Tuple

class VDFParser:
    """Parser for Valve Data Format (VDF) files"""
    
    @staticmethod
    def parse(content: str) -> dict:
        """
        Parse VDF content into a Python dictionary
        
        Args:
            content: String containing VDF data
            
        Returns:
            Dict containing parsed data structure
        """
        lines = content.strip().split('\n')
        return VDFParser._parse_section(lines, 0)[0]
    
    @staticmethod
    def _parse_section(lines: List[str], start_idx: int) -> tuple:
        """
        Recursively parse a VDF section
        
        Args:
            lines: List of file lines
            start_idx: Starting line index
            
        Returns:
            Tuple of (parsed_dict, ending_index)
        """
        result = {}
        i = start_idx
        current_key = None
        
        while i < len(lines):
            line = lines[i].strip()
            
            if not line or line.startswith('//'):
                i += 1
                continue
                
            if '}' in line:
                return result, i
                
            if '{' in line:
                if current_key:
                    subsection, new_idx = VDFParser._parse_section(lines, i + 1)
                    result[current_key] = subsection
                    i = new_idx + 1
                    current_key = None
                continue
                
            parts = re.findall(r'"([^"]*)"', line)
            if len(parts) >= 2:
                current_key = parts[0]
                value = parts[1]
                result[current_key] = value
            elif len(parts) == 1:
                current_key = parts[0]
            
            i += 1
            
        return result, i

class ItemFilter:
    """Helper class for filtering TF2 items"""
    
    @staticmethod
    def _get_prefab_data(prefabs: Dict, prefab_name: str, field: str) -> Optional[str]:
        """
        Recursively get data from prefab
        
        Args:
            prefabs: Dictionary of all prefabs
            prefab_name: Name of the prefab to check
            field: Field to look for
            
        Returns:
            Value if found, None otherwise
        """
        if prefab_name not in prefabs:
            return None
            
        prefab = prefabs[prefab_name]
        
        # Проверяем текущий префаб
        if field in prefab:
            return prefab[field]
            
        # Проверяем базовый префаб, если есть
        if 'prefab' in prefab:
            return ItemFilter._get_prefab_data(prefabs, prefab['prefab'], field)
            
        return None

    @staticmethod
    def filter_by_criteria(items: Dict, criteria: Dict, prefabs: Dict) -> Dict:
        """
        Filter items by multiple criteria
        
        Args:
            items: Dictionary of items to filter
            criteria: Dictionary of criteria {field: value}
            prefabs: Dictionary of prefabs
            
        Returns:
            Filtered items dictionary
        """
        result = {}
        
        for item_id, item in items.items():
            matches = True
            
            for field, required_value in criteria.items():
                value = None
                
                # Сначала проверяем сам предмет
                if field in item:
                    value = item[field]
                # Затем проверяем в префабе
                elif 'prefab' in item:
                    value = ItemFilter._get_prefab_data(prefabs, item['prefab'], field)
                    
                if not value or value != required_value:
                    matches = False
                    break
            
            if matches:
                result[item_id] = item
                
        return result

class TF2ItemsParser:
    """Main class for working with TF2 items data"""
    
    @staticmethod
    def get_nested_value(data: Dict, path: str) -> Optional[Any]:
        """
        Get value from nested dictionary using dot notation
        
        Args:
            data: Dictionary to search in
            path: Path to value using dot notation (e.g. 'visuals.player_bodygroups.hat')
            
        Returns:
            Value if found, None otherwise
        """
        current = data
        for part in path.split('.'):
            if isinstance(current, dict):
                current = current.get(part)
            else:
                return None
        return current
        
    def get_param_inChaos(self, item: Dict, search_param: str, *block_names: str) -> List[Dict]:
        """
        Search for parameters in nested dictionary structure with contextual path handling
        
        Args:
            item: Item dictionary to search in
            search_param: Parameter name to search for
            block_names: Optional specific block names to look in
            
        Returns:
            List of dictionaries containing found parameters with their paths and values.
            The result structure will look like:
            [
                {
                    "block_name": "main_block",
                    "additional_blocks": ["sub_block1", "sub_block2"],
                    "end": {"key": "value"} or {"0": "value"} for numbered blocks
                }
            ]
        """
        def search_recursive(data: Dict, current_path: List[str], results: List[Dict]) -> None:
            if not isinstance(data, dict):
                return
                
            # Если указаны конкретные блоки и текущий путь начинается не с них - пропускаем
            if block_names and current_path and current_path[0] not in block_names:
                return
                
            # Проверяем, есть ли искомый параметр в текущем блоке
            if search_param in data:
                value = data[search_param]
                
                # Получаем базовый путь и последний элемент (если есть)
                base_path = current_path[:-1] if current_path else []
                last_key = current_path[-1] if current_path else None
                
                result = {
                    "block_name": base_path[0] if base_path else "root",
                    "additional_blocks": base_path[1:] if len(base_path) > 1 else []
                }
                
                if last_key and last_key.isdigit():
                    # Если последний элемент пути - число, используем его как ключ
                    result["end"] = {last_key: value}
                elif isinstance(value, dict):
                    # Для словарей сохраняем структуру
                    result["end"] = value
                else:
                    # Для простых значений
                    if last_key:
                        result["end"] = {last_key: value}
                    else:
                        result["end"] = value
                        
                results.append(result)
                
            # Ищем во вложенных блоках
            for key, value in data.items():
                if isinstance(value, dict):
                    search_recursive(value, current_path + [key], results)
                    
                # Особая обработка для списков словарей
                elif isinstance(value, dict) and any(isinstance(v, dict) for v in value.values()):
                    for subkey, subvalue in value.items():
                        if isinstance(subvalue, dict):
                            search_recursive(subvalue, current_path + [key, subkey], results)
        
        results = []
        search_recursive(item, [], results)
        return results[0] if len(results) > 0 else results

    def get_item_info(self, item: Dict) -> Dict:
        """
        Get comprehensive item information
        
        Args:
            item: Item dictionary
            
        Returns:
            Dictionary with all available item information
        """
        # Получаем информацию из префаба, если он есть
        prefab_data = {}
        if 'prefab' in item:
            prefab_name = item['prefab']
            if self.data and 'items_game' in self.data and 'prefabs' in self.data['items_game']:
                prefab = self.data['items_game']['prefabs'].get(prefab_name, {})
                prefab_data = self.get_item_info(prefab)  # Рекурсивно получаем данные из префаба
        
        # Основная информация
        basic_info = {
            'name': item.get('name'),
            'item_class': item.get('item_class'),
            'item_quality': item.get('item_quality'),
            'item_description': item.get('item_description'),
            'model_player': item.get('model_player'),
            'mouse_pressed_sound': item.get('mouse_pressed_sound'),
            'drop_sound': item.get('drop_sound'),
            'equip_region': item.get('equip_region'),
            'image_inventory': item.get('image_inventory'),
            'image_inventory_size_w': item.get('image_inventory_size_w'),
            'image_inventory_size_h': item.get('image_inventory_size_h'),
        }
        
        # Классы, которые могут использовать предмет
        classes = item.get('used_by_classes', {})
        if classes:
            basic_info['used_by_classes'] = [
                class_name for class_name, value in classes.items()
                if value == '1'
            ]
        
        # Возможности предмета
        capabilities = item.get('capabilities', {})
        if capabilities:
            basic_info['capabilities'] = capabilities
            basic_info['paintable'] = capabilities.get('paintable') == '1'
            
        # Визуальные эффекты и bodygroups
        visuals = item.get('visuals', {})
        if visuals:
            bodygroups = self.get_nested_value(visuals, 'player_bodygroups')
            if bodygroups:
                basic_info['bodygroups'] = bodygroups
                
            # Добавляем другие визуальные эффекты, если они есть
            styles = self.get_nested_value(visuals, 'styles')
            if styles:
                basic_info['styles'] = styles
                
        # Объединяем данные из префаба и текущего предмета
        # Данные текущего предмета имеют приоритет
        result = {**prefab_data, **basic_info}
        
        # Удаляем None значения для чистоты
        return {k: v for k, v in result.items() if v is not None}
    
    def __init__(self, file_path: str):
        """
        Initialize parser with items_game.txt file path
        
        Args:
            file_path: Path to items_game.txt file
        """
        self.file_path = file_path
        self.data = None
        
    def load(self) -> None:
        """Load and parse the items file"""
        print(f"Attempting to load file: {self.file_path}")
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                print(f"File loaded, content length: {len(content)} bytes")
            parsed_data = VDFParser.parse(content)
            print(f"Data parsed, keys: {list(parsed_data.keys() if parsed_data else [])}")
            self.data = parsed_data
        
        except Exception as e:
            print(f"Error loading file: {e}")
            raise
        
    def save_json(self, output_path: str) -> None:
        """
        Save parsed data to JSON file
        
        Args:
            output_path: Path where to save JSON file
        """
        if not self.data:
            print("Warning: No data loaded. Call load() first")
            return
            
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2)
            print(f"Data successfully saved to {output_path}")
        except Exception as e:
            print(f"Error saving JSON file: {e}")
            raise
            
    def get_all_items(self) -> Dict:
        """
        Get all items from the parsed data
        
        Returns:
            Dictionary containing all items
        """
        if not self.data or 'items_game' not in self.data or 'items' not in self.data['items_game']:
            raise ValueError("No items data loaded")
        return self.data['items_game']['items']
        
    def get_item_by_key(self, key: str) -> Optional[Dict]:
        """
        Get item by its key
        
        Args:
            key: Item key/ID
                
        Returns:
            Item dictionary if found, None otherwise
        """
        if not isinstance(self.data, dict):
            return None
            
        items_game = self.data.get('items_game')
        if not isinstance(items_game, dict):
            return None
            
        items = items_game.get('items')
        if not isinstance(items, dict):
            return None
            
        return items.get(str(key))
        
    def get_item_by_name(self, name: str) -> Optional[Tuple[str, Dict]]:
        """
        Get item by its name
    
        Args:
            name: Item name
        
        Returns:
            Tuple of (index, item) if found, None otherwise
        """
        items = self.get_all_items()
        for index, item in items.items():
            if 'name' in item and item['name'] in name:
                return (index, item)
        return None
    
    def get_items_by_name(self, name: str) -> List[Tuple[int, Dict]]:
        """
        Get items by name with flexible search
    
        Args:
            name: Item name to search for (supports partial matches)
        
        Returns:
            List of tuples containing (item_index, item_dictionary) for all matching items
            Results are sorted by relevance (exact matches first, then partial matches)
        """
        items = self.get_all_items()
        found_items = []
        search_term = name.lower().strip()
        
        if not search_term:
            return found_items
        
        exact_matches = []
        partial_matches = []
        
        for index, item in items.items():
            item_name = item['name'].lower()
            
            # Точное совпадение (игнорируя регистр)
            if item_name == search_term:
                exact_matches.append((index, item))
                continue
                
            # Поиск по частичному совпадению
            if search_term in item_name:
                partial_matches.append((index, item))
                continue
                
            # Поиск по отдельным словам
            search_words = search_term.split()
            item_words = item_name.split()
            
            # Проверяем, содержит ли название предмета все слова из поискового запроса
            if all(any(search_word in item_word for item_word in item_words) 
                for search_word in search_words):
                partial_matches.append((index, item))
        
        # Возвращаем сначала точные совпадения, потом частичные
        return exact_matches + partial_matches
    
    def get_items_by_class(self, class_name: str, item_slot: Optional[str] = None) -> Dict:
        """
        Get items for specific class, optionally filtered by item slot
        
        Args:
            class_name: Class name (e.g., "Scout", "Soldier")
            item_slot: Optional item slot filter
            
        Returns:
            Dictionary of matching items
        """
        if not self.data or 'items_game' not in self.data:
            return {}
            
        items = self.data['items_game'].get('items', {})
        prefabs = self.data['items_game'].get('prefabs', {})
        
        criteria = {'used_by_classes': {class_name.lower(): '1'}}
        if item_slot:
            criteria['item_slot'] = item_slot
            
        return ItemFilter.filter_by_criteria(items, criteria, prefabs)
        
    def get_items_by_slot(self, slot: str) -> Dict:
        """
        Get items for specific slot
        
        Args:
            slot: Item slot name
            
        Returns:
            Dictionary of matching items
        """
        if not self.data or 'items_game' not in self.data:
            return {}
            
        items = self.data['items_game'].get('items', {})
        prefabs = self.data['items_game'].get('prefabs', {})
        
        return ItemFilter.filter_by_criteria(items, {'item_slot': slot}, prefabs)
        
    def filter_items(self, criteria: Dict) -> Dict:
        """
        Filter items by custom criteria
        
        Args:
            criteria: Dictionary of criteria {field: value}
            
        Returns:
            Dictionary of matching items
        """
        if not self.data or 'items_game' not in self.data:
            return {}
            
        items = self.data['items_game'].get('items', {})
        prefabs = self.data['items_game'].get('prefabs', {})
        
        # Преобразуем критерий класса в правильный формат
        if 'used_by_classes' in criteria:
            criteria['used_by_classes'] = {criteria['used_by_classes']: '1'}
            
        return ItemFilter.filter_by_criteria(items, criteria, prefabs)
