#!/usr/bin/env python3
import json
import sys
import os
import requests
import re
import time
from datetime import datetime
from PIL import Image
from io import BytesIO

# Configuration API
API_BASE_URL = "https://db.ygoprodeck.com/api/v7"
CARDSETS_ENDPOINT = f"{API_BASE_URL}/cardsets.php"
CARDINFO_ENDPOINT = f"{API_BASE_URL}/cardinfo.php"

class YuGiOhAutoSync:
    def __init__(self):
        self.existing_sets = self.load_existing_sets()
        self.max_archetype_id = self.get_max_archetype_id()
        self.max_collection_id = self.get_max_collection_id()
        
    def fetch_all_cardsets(self):
        """Récupère tous les sets depuis l'API YGOPRODeck"""
        try:
            print("🔄 Récupération de tous les sets depuis l'API...")
            response = requests.get(CARDSETS_ENDPOINT, timeout=30)
            response.raise_for_status()
            
            cardsets_data = response.json()
            
            # 🐛 DEBUG: Dump des données de sets
            print(f"\n🐛 DEBUG - Structure d'un set (premier élément):")
            if cardsets_data:
                import pprint
                pprint.pprint(cardsets_data[0])
                print(f"\n🐛 DEBUG - Clés disponibles dans un set: {list(cardsets_data[0].keys())}")
            print(f"✅ {len(cardsets_data)} sets récupérés depuis l'API")
            return cardsets_data
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Erreur lors de la récupération des sets: {e}")
            return []
        except json.JSONDecodeError as e:
            print(f"❌ Erreur de décodage JSON: {e}")
            return []
    
    def load_existing_sets(self):
        """Charge tous les sets existants depuis les dossiers locaux"""
        existing_sets = set()
        
        # Vérifier les archétypes
        archetypes_dir = "archetypes"
        if os.path.exists(archetypes_dir):
            for filename in os.listdir(archetypes_dir):
                if filename.endswith('.json') and filename != 'base.json':
                    set_code = filename.replace('.json', '')
                    existing_sets.add(set_code)
        
        # Vérifier les collections
        collections_dir = "collections"
        if os.path.exists(collections_dir):
            for filename in os.listdir(collections_dir):
                if filename.endswith('.json') and filename != 'base.json':
                    set_code = filename.replace('.json', '')
                    existing_sets.add(set_code)
        
        # Vérifier les cartes
        cards_dir = "cards"
        if os.path.exists(cards_dir):
            for filename in os.listdir(cards_dir):
                if filename.endswith('.json') and filename != 'base.json':
                    set_code = filename.replace('.json', '')
                    existing_sets.add(set_code)
        
        print(f"📁 {len(existing_sets)} sets existants trouvés localement")
        return existing_sets
    
    def get_max_archetype_id(self):
        """Récupère l'ID maximum utilisé dans tous les fichiers d'archétypes"""
        max_id = 0
        archetypes_dir = "archetypes"
        
        if os.path.exists(archetypes_dir):
            for filename in os.listdir(archetypes_dir):
                if filename.endswith('.json'):
                    filepath = os.path.join(archetypes_dir, filename)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as file:
                            archetype_data = json.load(file)
                            for archetype in archetype_data:
                                try:
                                    archetype_id = int(archetype.get('id', 0))
                                    max_id = max(max_id, archetype_id)
                                except (ValueError, TypeError):
                                    pass
                    except Exception as e:
                        print(f"⚠️ Erreur lors du chargement de {filepath}: {e}")
        
        return max_id
    
    def get_max_collection_id(self):
        """Récupère l'ID de collection le plus élevé depuis les fichiers existants"""
        max_id = 0
        collections_dir = "collections"
        
        if os.path.exists(collections_dir):
            for filename in os.listdir(collections_dir):
                if filename.endswith('.json') and filename != 'base.json':
                    filepath = os.path.join(collections_dir, filename)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            if isinstance(data, list) and len(data) > 0:
                                collection_id = data[0].get('id', 0)
                                if isinstance(collection_id, int):
                                    max_id = max(max_id, collection_id)
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue
        
        return max_id
    
    def normalize_set_name(self, set_name):
        """Normalise le nom d'un set pour créer un code de fichier"""
        # Supprimer les caractères spéciaux et espaces
        normalized = re.sub(r'[^a-zA-Z0-9]', '', set_name.lower())
        # Limiter à 10 caractères maximum
        return normalized[:10] if len(normalized) > 10 else normalized
    
    def compare_sets(self, api_sets):
        """Compare les sets de l'API avec les sets existants"""
        new_sets = []
        
        for api_set in api_sets:
            set_name = api_set.get('set_name', '')
            set_code = api_set.get('set_code', '')
            
            # SOLUTION 1: Utiliser prioritairement le set_code
            # Essayer différentes variantes du code pour la comparaison
            possible_codes = [
                set_code.lower(),                   # Code principal (ex: "ys15", "stax")
                self.normalize_set_name(set_code),  # Code normalisé
                self.normalize_set_name(set_name),  # Nom normalisé (fallback)
                set_name.lower().replace(' ', '').replace('-', '')[:10]  # Nom simplifié (fallback)
            ]
            
            # Vérifier si ce set existe déjà
            exists = any(code in self.existing_sets for code in possible_codes)
            
            if not exists:
                new_sets.append({
                    'api_data': api_set,
                    'suggested_code': possible_codes[0]  # Utiliser le set_code.lower() comme suggestion
                })
        
        print(f"🆕 {len(new_sets)} nouveaux sets détectés")
        return new_sets
    
    def fetch_cards_for_set(self, set_name):
        """Récupère toutes les cartes d'un set spécifique"""
        try:
            print(f"🔄 Récupération des cartes pour le set: {set_name}")
            
            # Première tentative avec language=fr
            print(f"🇫🇷 Tentative avec language=fr...")
            params_fr = {'cardset': set_name, 'language': 'fr'}
            response = requests.get(CARDINFO_ENDPOINT, params=params_fr, timeout=30)
            
            if response.status_code == 200:
                try:
                    cards_data = response.json()
                    if 'data' in cards_data and cards_data['data']:
                        cards = cards_data['data']
                        print(f"✅ {len(cards)} cartes récupérées en français pour {set_name}")
                        return cards
                    else:
                        print(f"⚠️ Pas de données avec language=fr, tentative sans...")
                except json.JSONDecodeError:
                    print(f"⚠️ Erreur JSON avec language=fr, tentative sans...")
            else:
                print(f"⚠️ Erreur HTTP {response.status_code} avec language=fr, tentative sans...")
            
            # Deuxième tentative sans language (par défaut en anglais)
            print(f"🇬🇧 Tentative sans paramètre language...")
            params = {'cardset': set_name}
            response = requests.get(CARDINFO_ENDPOINT, params=params, timeout=30)
            response.raise_for_status()
            
            cards_data = response.json()
            if 'data' in cards_data:
                cards = cards_data['data']
                print(f"✅ {len(cards)} cartes récupérées en anglais pour {set_name}")
                return cards
            else:
                print(f"⚠️ Aucune carte trouvée pour {set_name}")
                return []
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Erreur lors de la récupération des cartes pour {set_name}: {e}")
            return []
        except json.JSONDecodeError as e:
            print(f"❌ Erreur de décodage JSON pour {set_name}: {e}")
            return []
    
    def create_collection_structure(self, set_data, set_code, cards):
        """Crée la structure JSON pour une collection (format array avec un objet)"""
        
        # Déterminer le type de set basé sur le nom
        set_name_lower = set_data['set_name'].lower()
        if 'starter' in set_name_lower or 'deck' in set_name_lower:
            set_type = "starter"
        elif 'booster' in set_name_lower:
            set_type = "booster"
        elif 'structure' in set_name_lower:
            set_type = "structure"
        else:
            set_type = "booster"  # par défaut
        
        collection = {
            "id": set_code.lower(),  # Utiliser le code du set en minuscules
            "name": set_data['set_name'],
            "nameEn": set_data['set_name'],
            "type": set_type,
            "codePrefix": f"{set_code.upper()}-",  # Ajouter le préfixe de code
            "releaseDate": datetime.now().strftime("%Y-%m-%d")
        }
        
        # Retourner un array avec un seul objet (format existant)
        return [collection]
    
    def create_cards_structure(self, cards, set_code):
        """Crée la structure JSON pour les cartes d'un set (format attendu)"""
        cards_structure = []
        
        for card in cards:
            # Convertir l'ID de -EN vers -FR
            card_id_fr = str(card.get('id')).replace('-EN', '-FR') if card.get('id') else None
            print(card)
            # Déterminer le type de monstre et les propriétés
            card_type = card.get('type', '')
            is_effect = 'Effect' in card_type
            is_pendulum = 'Pendulum' in card_type
            is_link = 'Link' in card_type
            
            # Extraire le type de base (Normal, Effect, etc.)
            if 'Normal' in card_type:
                base_type = 'Normal'
            elif 'Effect' in card_type:
                base_type = 'Effect'
            elif 'Fusion' in card_type:
                base_type = 'Fusion'
            elif 'Synchro' in card_type:
                base_type = 'Synchro'
            elif 'Xyz' in card_type:
                base_type = 'Xyz'
            elif 'Link' in card_type:
                base_type = 'Link'
            elif 'Ritual' in card_type:
                base_type = 'Ritual'
            elif 'Spell' in card_type:
                base_type = 'Spell'
            elif 'Trap' in card_type:
                base_type = 'Trap'
            else:
                base_type = 'Normal'
            
            card_structure = {
                "id": card_id_fr,
                "name": card.get('name'),
                "nameEn": card.get('name'),
                "attribute": card.get('attribute'),
                "atk": card.get('atk'),
                "def": card.get('def'),
                "level": card.get('level'),
                "monsterType": card.get('race'),  # race -> monsterType
                "type": base_type,  # Type simplifié
                "isEffect": is_effect,
                "isPendulum": is_pendulum,
                "isLink": is_link,
                "description": card.get('desc', '')  # desc -> description
            }
            
            # Ajouter archetype seulement s'il existe et n'est pas vide
            archetype = card.get('archetype', '').strip()
            if archetype:
                card_structure["archetype"] = archetype
            
            cards_structure.append(card_structure)
        
        return cards_structure
    
    def create_collection_cards_structure(self, cards, set_code, collection_id, dry_run=False):
        """Crée la structure JSON pour collection-cards avec la logique correcte pour les IDs français"""
        collection_cards = []
        card_counter = 1
        
        for card in cards:
            # Récupérer l'ID original de la carte
            original_card_id = card.get('id')
            card_name = card.get('name', 'Unknown')
            card_type = card.get('type', 'Unknown')
            card_race = card.get('race', 'Unknown')
            card_attribute = card.get('attribute', 'Unknown')
            
            # Chercher le bon set dans les card_sets de la carte
            card_id_fr = None
            matching_set_code = None
            
            if 'card_sets' in card and card['card_sets']:
                for card_set in card['card_sets']:
                    card_set_name = card_set.get('set_name', '').lower()
                    card_set_code = card_set.get('set_code', '')
                    
                    # Normaliser le nom du set pour la comparaison
                    normalized_set_name = self.normalize_set_name(card_set_name)
                    
                    # Vérifier si ce set correspond à notre recherche
                    if (normalized_set_name == set_code.lower() or 
                        card_set_code.lower().startswith(set_code.lower())):
                        
                        matching_set_code = card_set_code
                        # Convertir EN en FR dans le code du set
                        if '-EN' in card_set_code:
                            card_id_fr = card_set_code.replace('-EN', '-FR')
                        else:
                            # Si pas de -EN, ajouter -FR avec un numéro
                            card_id_fr = f"{set_code.upper()}-FR{card_counter:03d}"
                        break
            
            # Si aucun set correspondant trouvé, utiliser une logique de fallback
            if not card_id_fr:
                card_id_fr = f"{set_code.upper()}-FR{card_counter:03d}"
                matching_set_code = f"{set_code.upper()}-EN{card_counter:03d}"
            
            if dry_run:
                print(f"\n=== CARTE #{card_counter} ===")
                print(f"Nom: {card_name}")
                print(f"Type: {card_type}")
                print(f"Race: {card_race}")
                print(f"Attribut: {card_attribute}")
                print(f"ID original API: {original_card_id}")
                print(f"Set code recherché: {set_code}")
                print(f"Collection ID: {collection_id}")
                
                # Afficher les images disponibles
                if 'card_images' in card and card['card_images']:
                    print(f"Images disponibles: {len(card['card_images'])}")
                    for i, img in enumerate(card['card_images']):
                        print(f"  Image {i+1}: {img.get('image_url', 'N/A')}")
                else:
                    print("Aucune image disponible")
                
                # Afficher les sets de la carte
                if 'card_sets' in card and card['card_sets']:
                    print(f"Sets de la carte: {len(card['card_sets'])}")
                    for card_set in card['card_sets']:
                        set_name = card_set.get('set_name', 'N/A')
                        set_code_display = card_set.get('set_code', 'N/A')
                        marker = " ← CORRESPONDANCE" if set_code_display == matching_set_code else ""
                        print(f"  Set: {set_name} - Code: {set_code_display}{marker}")
                else:
                    print("Aucun set trouvé pour cette carte")
                
                print(f"Set code correspondant trouvé: {matching_set_code}")
                print(f"ID français généré: {card_id_fr}")
                print(f"Structure collection-cards qui sera créée:")
                print(f"  id: {card_id_fr}")
                print(f"  cardId: {card_id_fr}")
                print(f"  collectionId: {set_code.upper()}")
                print("=" * 50)
            
            collection_card = {
                "id": card_id_fr,
                "cardId": card_id_fr,
                "collectionId": set_code.upper()
            }
            
            collection_cards.append(collection_card)
            card_counter += 1
        
        if dry_run:
            print(f"\n🔍 RÉSUMÉ DU DRY-RUN:")
            print(f"Total de cartes traitées: {len(collection_cards)}")
            print(f"Set code utilisé: {set_code}")
            print(f"Collection ID utilisé: {set_code.upper()}")
            print(f"Fichier qui serait créé: collection-cards/{set_code}.json")
            return None  # Ne pas retourner les données en mode dry-run
        
        return collection_cards
    
    def save_json_file(self, data, filepath):
        """Sauvegarde des données JSON dans un fichier"""
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, 'w', encoding='utf-8') as file:
                json.dump(data, file, ensure_ascii=False, indent=2)
            print(f"✅ Fichier sauvegardé: {filepath}")
            return True
        except Exception as e:
            print(f"❌ Erreur lors de la sauvegarde de {filepath}: {e}")
            return False
    
    def download_card_image(self, card_id, image_url):
        """Télécharge et convertit une image de carte en WebP"""
        output_dir = "cards-image"
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"{card_id}.webp")
        
        # Vérifier si l'image existe déjà
        if os.path.exists(output_path):
            return True
        
        try:
            response = requests.get(image_url, timeout=30)
            response.raise_for_status()
            
            image = Image.open(BytesIO(response.content))
            
            # Convertir en RGB si nécessaire
            if image.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', image.size, (255, 255, 255))
                if image.mode == 'P':
                    image = image.convert('RGBA')
                background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
                image = background
            elif image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Sauvegarder en WebP
            image.save(output_path, "WEBP", quality=95)
            return True
            
        except Exception as e:
            print(f"⚠️ Erreur téléchargement image {card_id}: {e}")
            return False
    
    def download_collection_image(self, collection_code, image_url):
        os.makedirs("collections-image", exist_ok=True)
        filename = f"{collection_code}.webp"
        filepath = os.path.join("collections-image", filename)
        
        if os.path.exists(filepath):
            print(f"Image already exists: {filepath}")
            return
        
        try:
            response = requests.get(image_url)
            response.raise_for_status()
            
            image = Image.open(BytesIO(response.content))
            image = image.convert("RGB")
            image.save(filepath, "WEBP", quality=85)
            print(f"Downloaded and saved: {filepath}")
        except Exception as e:
            print(f"Error downloading image for {collection_code}: {e}")
    
    def load_existing_archetypes(self):
        """Charge tous les archétypes existants depuis tous les fichiers JSON"""
        existing_archetypes = set()
        archetypes_dir = "archetypes"
        
        if not os.path.exists(archetypes_dir):
            return existing_archetypes
            
        for filename in os.listdir(archetypes_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(archetypes_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if isinstance(data, list):
                            for archetype in data:
                                if 'nameEn' in archetype:
                                    existing_archetypes.add(archetype['nameEn'])
                except (json.JSONDecodeError, FileNotFoundError):
                    continue
                    
        return existing_archetypes

    def extract_unique_archetypes(self, cards):
        """Extrait les archétypes uniques des cartes qui n'existent pas déjà"""
        # Charger les archétypes existants
        existing_archetypes = self.load_existing_archetypes()
        
        archetypes = set()
        for card in cards:
            archetype = card.get('archetype', '').strip()
            if archetype and archetype not in existing_archetypes:
                archetypes.add(archetype)
        
        return list(archetypes)

    def create_archetype_structure(self, archetypes, set_code):
        """Crée la structure JSON pour les archétypes (seulement les nouveaux)"""
        if not archetypes:
            return []
            
        archetype_structures = []
        for archetype_name in archetypes:
            self.max_archetype_id += 1
            archetype = {
                "id": self.max_archetype_id,
                "name": archetype_name,
                "nameEn": archetype_name
            }
            archetype_structures.append(archetype)
        
        return archetype_structures

    def process_new_set(self, set_data, dry_run=False):
        set_code = set_data['set_code']
        set_name = set_data.get('set_name', set_code)
        # Convertir le set_code en minuscules pour les noms de fichiers
        file_code = set_code.lower()
        print(f"Processing new set: {set_code} (dry_run={dry_run})")
        
        archetype_created = False
        
        try:
            # Utiliser set_name pour l'API
            cards = self.fetch_cards_for_set(set_name)
            if not cards:
                print(f"No cards found for set {set_name}")
                return False, archetype_created
            
            # Download collection image if available (seulement si pas dry_run)
            if not dry_run and 'set_image' in set_data and set_data['set_image'].strip():
                image_url = set_data['set_image'].strip()
                print(f"Downloading collection image for {file_code}: {image_url}")
                self.download_collection_image(file_code, image_url)
            elif dry_run and 'set_image' in set_data and set_data['set_image'].strip():
                print(f"[DRY RUN] Would download collection image for {file_code}: {set_data['set_image'].strip()}")
            
            # Extraire les archétypes uniques des cartes (seulement les nouveaux)
            unique_archetypes = self.extract_unique_archetypes(cards)
            
            # Créer le fichier archetype seulement s'il y a de nouveaux archétypes
            if unique_archetypes:
                archetype_data = self.create_archetype_structure(unique_archetypes, file_code)
                archetype_filename = f"archetypes/{file_code}.json"
                if not dry_run:
                    with open(archetype_filename, 'w', encoding='utf-8') as f:
                        json.dump(archetype_data, f, ensure_ascii=False, indent=2)
                    print(f"Saved archetype data: {archetype_filename} with new archetypes: {unique_archetypes}")
                    archetype_created = True
                else:
                    print(f"[DRY RUN] Would save archetype data: {archetype_filename} with new archetypes: {unique_archetypes}")
                    archetype_created = True  # Pour le dry run aussi
            else:
                print(f"No new archetypes found for {set_code}, skipping archetype file creation")
            
            # Generate collection data with updated releaseDate
            collection_data = self.create_collection_structure(set_data, file_code, cards)
            # Update releaseDate from tcg_date if available
            if 'tcg_date' in set_data and set_data['tcg_date']:
                if isinstance(collection_data, list) and len(collection_data) > 0:
                    collection_data[0]['releaseDate'] = set_data['tcg_date']
            
            collection_filename = f"collections/{file_code}.json"
            if not dry_run:
                with open(collection_filename, 'w', encoding='utf-8') as f:
                    json.dump(collection_data, f, ensure_ascii=False, indent=2)
                print(f"Saved collection data: {collection_filename}")
            else:
                print(f"[DRY RUN] Would save collection data: {collection_filename}")
            
            # Generate cards data
            cards_data = self.create_cards_structure(cards, file_code)
            cards_filename = f"cards/{file_code}.json"
            if not dry_run:
                with open(cards_filename, 'w', encoding='utf-8') as f:
                    json.dump(cards_data, f, ensure_ascii=False, indent=2)
                print(f"Saved cards data: {cards_filename}")
            else:
                print(f"[DRY RUN] Would save cards data: {cards_filename}")
            
            # Generate collection-cards data
            collection_cards_data = self.create_collection_cards_structure(cards, file_code, file_code.upper(), dry_run)
            if collection_cards_data and not dry_run:
                collection_cards_filename = f"collection-cards/{file_code}.json"
                with open(collection_cards_filename, 'w', encoding='utf-8') as f:
                    json.dump(collection_cards_data, f, ensure_ascii=False, indent=2)
                print(f"Saved collection-cards data: {collection_cards_filename}")
            elif collection_cards_data and dry_run:
                print(f"[DRY RUN] Would save collection-cards data: collection-cards/{file_code}.json")
            
            # Download card images (seulement si pas dry_run)
            if not dry_run:
                for card in cards:
                    if 'card_images' in card and card['card_images']:
                        image_url = card['card_images'][0]['image_url']
                        self.download_card_image(card['id'], image_url)
            else:
                print(f"[DRY RUN] Would download {len(cards)} card images")
            
            print(f"✅ Set {set_name} traité avec succès (dry_run={dry_run})")
            return True
            
        except Exception as e:
            print(f"Error processing set {set_code}: {str(e)}")
            return False, archetype_created
    
    def update_manifest(self, new_sets_processed=None, sets_with_archetypes=None):
        """Met à jour le fichier manifest.json avec les nouveaux sets"""
        manifest_path = "manifest.json"
        
        try:
            # Charger le manifest existant
            if os.path.exists(manifest_path):
                with open(manifest_path, 'r', encoding='utf-8') as file:
                    manifest = json.load(file)
            else:
                # Structure par défaut si le manifest n'existe pas
                manifest = {
                    "version": "1.0.0",
                    "lastUpdated": "",
                    "data": {
                        "cards": {
                            "baseFile": "cards/base.json",
                            "updates": []
                        },
                        "collections": {
                            "baseFile": "collections/base.json",
                            "updates": []
                        },
                        "collectionCards": {
                            "baseFile": "collection-cards/base.json",
                            "updates": []
                        },
                        "archetypes": {
                            "baseFile": "archetypes/base.json",
                            "updates": []
                        }
                    }
                }
            
            # Vérifier et initialiser les structures manquantes
            if "data" not in manifest:
                manifest["data"] = {}
            
            if "cards" not in manifest["data"]:
                manifest["data"]["cards"] = {
                    "baseFile": "cards/base.json",
                    "updates": []
                }
            
            if "collections" not in manifest["data"]:
                manifest["data"]["collections"] = {
                    "baseFile": "collections/base.json",
                    "updates": []
                }
            
            if "collectionCards" not in manifest["data"]:
                manifest["data"]["collectionCards"] = {
                    "baseFile": "collection-cards/base.json",
                    "updates": []
                }
            
            if "archetypes" not in manifest["data"]:
                manifest["data"]["archetypes"] = {
                    "baseFile": "archetypes/base.json",
                    "updates": []
                }
            
            # S'assurer que les arrays updates existent
            for section in ["cards", "collections", "collectionCards", "archetypes"]:
                if "updates" not in manifest["data"][section]:
                    manifest["data"][section]["updates"] = []
            
            # Incrémenter la version
            version_parts = manifest["version"].split(".")
            version_parts[2] = str(int(version_parts[2]) + 1)
            manifest["version"] = ".".join(version_parts)
            current_time = datetime.now().isoformat() + "Z"
            manifest["lastUpdated"] = current_time
            
            # Ajouter les nouveaux sets aux updates si fournis
            if new_sets_processed:
                for set_code in new_sets_processed:
                    # Ajouter aux cards
                    cards_update = {
                        "file": f"cards/{set_code}.json",
                        "date": current_time
                    }
                    if cards_update not in manifest["data"]["cards"]["updates"]:
                        manifest["data"]["cards"]["updates"].append(cards_update)
                    
                    # Ajouter aux collections
                    collections_update = {
                        "file": f"collections/{set_code}.json",
                        "date": current_time
                    }
                    if collections_update not in manifest["data"]["collections"]["updates"]:
                        manifest["data"]["collections"]["updates"].append(collections_update)
                    
                    # Ajouter aux collectionCards
                    collection_cards_update = {
                        "file": f"collection-cards/{set_code}.json",
                        "date": current_time
                    }
                    if collection_cards_update not in manifest["data"]["collectionCards"]["updates"]:
                        manifest["data"]["collectionCards"]["updates"].append(collection_cards_update)
                    
                    # Ajouter aux archetypes SEULEMENT si le set a des archetypes
                    if sets_with_archetypes and set_code in sets_with_archetypes:
                        archetypes_update = {
                            "file": f"archetypes/{set_code}.json",
                            "date": current_time
                        }
                        if archetypes_update not in manifest["data"]["archetypes"]["updates"]:
                            manifest["data"]["archetypes"]["updates"].append(archetypes_update)
            
            # Sauvegarder
            with open(manifest_path, 'w', encoding='utf-8') as file:
                json.dump(manifest, file, ensure_ascii=False, indent=2)
            
            if new_sets_processed:
                print(f"✅ Manifest mis à jour vers la version {manifest['version']} avec {len(new_sets_processed)} nouveaux sets")
            else:
                print(f"✅ Manifest mis à jour vers la version {manifest['version']}")
            return True
            
        except Exception as e:
            print(f"❌ Erreur lors de la mise à jour du manifest: {e}")
            import traceback
            traceback.print_exc()  # Pour plus de détails sur l'erreur
            return False
    
    def run_sync(self, max_sets=None, dry_run=False):
        """Lance la synchronisation avec option dry-run"""
        try:
            print("🚀 Démarrage de la synchronisation Yu-Gi-Oh!")
            
            if dry_run:
                print("🔍 MODE DRY-RUN ACTIVÉ - Aucun fichier ne sera créé")
            
            # Récupérer tous les sets depuis l'API
            api_sets = self.fetch_all_cardsets()
            if not api_sets:
                print("❌ Impossible de récupérer les sets depuis l'API")
                return
            
            print(f"📊 {len(api_sets)} sets trouvés dans l'API")
            
            # Comparer avec les sets existants
            new_sets = self.compare_sets(api_sets)
            
            if not new_sets:
                print("✅ Aucun nouveau set à traiter")
                return
            
            print(f"🆕 {len(new_sets)} nouveaux sets détectés")
            
            # Limiter le nombre de sets si spécifié
            if max_sets:
                new_sets = new_sets[:max_sets]
                print(f"🔢 Limitation à {max_sets} sets")
            
            # Traiter chaque nouveau set
            processed_sets = []
            sets_with_archetypes = []
            for i, new_set in enumerate(new_sets, 1):
                # Accéder aux données correctement depuis la structure retournée par compare_sets
                api_data = new_set['api_data']
                set_name = api_data.get('set_name', 'Unknown Set')
                set_code = api_data.get('set_code', new_set['suggested_code'])
                
                success, has_archetypes = self.process_new_set(api_data, dry_run)
                if success:
                    processed_sets.append(set_code.lower())
                    if has_archetypes:
                        sets_with_archetypes.append(set_code.lower())
                
                # Pause entre les sets pour éviter de surcharger l'API
                if i < len(new_sets):
                    time.sleep(1)
            
            if not dry_run and processed_sets:
                # Mettre à jour le manifest
                self.update_manifest(processed_sets, sets_with_archetypes)
            
            if dry_run:
                print(f"\n🔍 DRY-RUN TERMINÉ:")
                print(f"  - {len(processed_sets)} sets auraient été traités")
                print(f"  - Aucun fichier créé")
                print(f"  - Manifest non modifié")
            else:
                print(f"\n✅ Synchronisation terminée: {len(processed_sets)} sets traités")
            
        except Exception as e:
            print(f"❌ Erreur lors de la synchronisation: {str(e)}")
            import traceback
            traceback.print_exc()

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Synchronisation automatique Yu-Gi-Oh!')
    parser.add_argument('--max-sets', type=int, help='Nombre maximum de sets à traiter')
    parser.add_argument('--dry-run', action='store_true', help='Aperçu sans modifications')
    
    args = parser.parse_args()
    
    sync = YuGiOhAutoSync()
    sync.run_sync(max_sets=args.max_sets, dry_run=args.dry_run)

if __name__ == "__main__":
    main()