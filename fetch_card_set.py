#!/usr/bin/env python3
import json
import sys
import os
import requests
import re
import time
from datetime import datetime

def load_existing_archetypes():
    """Charge tous les archétypes existants depuis le dossier archetypes"""
    archetypes = {}
    archetypes_dir = "archetypes"
    
    if os.path.exists(archetypes_dir):
        for filename in os.listdir(archetypes_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(archetypes_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as file:
                        archetype_data = json.load(file)
                        for archetype in archetype_data:
                            if 'nameEn' in archetype:
                                archetypes[archetype['nameEn']] = archetype
                except Exception as e:
                    print(f"Erreur lors du chargement de {filepath}: {e}")
    
    return archetypes

def save_archetype_to_file(archetype_name_en, filename="base.json"):
    """Ajoute un nouvel archétype au fichier spécifié"""
    filepath = os.path.join("archetypes", filename)
    
    # Charger le fichier existant ou créer une liste vide
    archetypes = []
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as file:
                archetypes = json.load(file)
        except Exception as e:
            print(f"Erreur lors du chargement de {filepath}: {e}")
    
    # Vérifier si l'archétype existe déjà
    for archetype in archetypes:
        if archetype.get('nameEn') == archetype_name_en:
            return  # L'archétype existe déjà
    
    # Générer un nouvel ID
    max_id = 0
    for archetype in archetypes:
        try:
            archetype_id = int(archetype.get('id', 0))
            max_id = max(max_id, archetype_id)
        except ValueError:
            pass
    
    new_id = str(max_id + 1)
    
    # Ajouter le nouvel archétype
    new_archetype = {
        "id": new_id,
        "name": archetype_name_en,  # À compléter manuellement
        "nameEn": archetype_name_en
    }
    
    archetypes.append(new_archetype)
    
    # Sauvegarder le fichier
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as file:
        json.dump(archetypes, file, ensure_ascii=False, indent=2)
    
    print(f"Nouvel archétype ajouté: {archetype_name_en} (ID: {new_id})")

def create_collection_file(name, card_set, code_prefix):
    """Crée le fichier de collection correspondant"""
    collection_data = [{
        "id": name,
        "name": card_set,
        "nameEn": card_set,
        "type": "",  # À compléter manuellement
        "codePrefix": code_prefix
    }]
    
    collection_file = f"collections/{name}.json"
    os.makedirs(os.path.dirname(collection_file), exist_ok=True)
    
    with open(collection_file, 'w', encoding='utf-8') as file:
        json.dump(collection_data, file, ensure_ascii=False, indent=2)
    
    print(f"Fichier de collection créé: {collection_file}")
    return True

def increment_version(version):
    """Incrémente la version (format x.y.z)"""
    try:
        parts = version.split('.')
        if len(parts) == 3:
            # Incrémenter la version patch (z)
            parts[2] = str(int(parts[2]) + 1)
            return '.'.join(parts)
        else:
            return version
    except:
        return version

def update_manifest(name, created_archetype_file=False):
    """Met à jour le manifest.json avec les nouveaux fichiers créés"""
    manifest_file = "manifest.json"
    current_time = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    
    try:
        # Charger le manifest existant
        manifest = {}
        if os.path.exists(manifest_file):
            with open(manifest_file, 'r', encoding='utf-8') as file:
                manifest = json.load(file)
        
        # Incrémenter la version
        current_version = manifest.get('version', '0.0.0')
        new_version = increment_version(current_version)
        manifest['version'] = new_version
        manifest['lastUpdated'] = current_time
        
        # Initialiser la structure data si elle n'existe pas
        if 'data' not in manifest:
            manifest['data'] = {}
        
        # Mettre à jour les sections cards, collections, collectionCards
        sections = [
            ('cards', f'cards/{name}.json'),
            ('collections', f'collections/{name}.json'),
            ('collectionCards', f'collection-cards/{name}.json')
        ]
        
        # Ajouter archetypes si un fichier a été créé
        if created_archetype_file:
            sections.append(('archetypes', f'archetypes/{name}.json'))
        
        for section_name, file_path in sections:
            if section_name not in manifest['data']:
                manifest['data'][section_name] = {
                    'baseFile': f'{section_name.replace("collectionCards", "collection-cards")}/base.json',
                    'updates': []
                }
            
            # Vérifier si le fichier existe déjà dans les updates
            updates = manifest['data'][section_name]['updates']
            file_exists = any(update['file'] == file_path for update in updates)
            
            if not file_exists:
                # Ajouter le nouveau fichier
                new_update = {
                    'file': file_path,
                    'date': current_time
                }
                updates.append(new_update)
                print(f"Ajouté au manifest: {file_path}")
            else:
                # Mettre à jour la date du fichier existant
                for update in updates:
                    if update['file'] == file_path:
                        update['date'] = current_time
                        print(f"Mis à jour dans le manifest: {file_path}")
                        break
        
        # Sauvegarder le manifest
        with open(manifest_file, 'w', encoding='utf-8') as file:
            json.dump(manifest, file, ensure_ascii=False, indent=2)
        
        print(f"Manifest mis à jour: version {current_version} -> {new_version}")
        return True
        
    except Exception as e:
        print(f"Erreur lors de la mise à jour du manifest: {e}")
        return False

def fetch_card_set(card_set, name, collection_id, code_prefix):
    """
    Récupère les informations des cartes d'un set spécifique depuis l'API YGOPRODeck
    et crée les fichiers JSON nécessaires
    """
    # Charger les archétypes existants
    existing_archetypes = load_existing_archetypes()
    new_archetypes = set()
    created_archetype_file = False
    
    # Créer le fichier de collection
    create_collection_file(name, card_set, code_prefix)
    
    # Construire l'URL de l'API avec langue française
    url_fr = f"https://db.ygoprodeck.com/api/v7/cardinfo.php?cardset={card_set}&language=fr"
    
    try:
        # Premier appel avec langue française
        print(f"Récupération des données pour le set: {card_set} (FR)")
        response_fr = requests.get(url_fr, timeout=30)
        response_fr.raise_for_status()
        api_data_fr = response_fr.json()
        
        # Vérifier si des cartes ont été trouvées
        if 'data' not in api_data_fr or not api_data_fr['data']:
            print(f"Aucune carte trouvée pour le set: {card_set}")
            return False
        
        # Attendre 5 secondes
        print("Attente de 5 secondes avant le second appel...")
        time.sleep(5)
        
        # Second appel sans langue pour récupérer les cartes manquantes
        url_en = f"https://db.ygoprodeck.com/api/v7/cardinfo.php?cardset={card_set}"
        print(f"Récupération des données pour le set: {card_set} (EN)")
        response_en = requests.get(url_en, timeout=30)
        response_en.raise_for_status()
        api_data_en = response_en.json()
        
        # Fusionner les données - ajouter les cartes manquantes
        cards_fr_ids = {str(card.get('id', '')) for card in api_data_fr['data']}
        
        if 'data' in api_data_en and api_data_en['data']:
            for card_en in api_data_en['data']:
                card_id = str(card_en.get('id', ''))
                if card_id not in cards_fr_ids:
                    print(f"Ajout de la carte manquante: {card_en.get('name', '')} (ID: {card_id})")
                    api_data_fr['data'].append(card_en)
        
        # Transformer les données au format souhaité
        formatted_cards = []
        collection_cards = []
        
        for card in api_data_fr['data']:
            card_type = card.get('type', '')
            typeline = card.get('typeline', '')
            is_effect = 'Effect' in typeline
            is_spell = 'Spell' in card_type
            is_trap = 'Trap' in card_type
            
            # Créer la carte formatée avec les champs communs
            formatted_card = {
                "id": str(card.get('id', '')),
                "name": card.get('name', ''),
                "nameEn": card.get('name_en', card.get('name', '')),  # Fallback sur name si name_en n'existe pas
                "description": card.get('desc', '')
            }

            formatted_card["isEffect"] = is_effect
            
            # Gérer les cartes magie et piège
            if is_spell:
                formatted_card["attribute"] = "SPELL"
                formatted_card["type"] = "Magic"
                formatted_card["isPendulum"] = False
                formatted_card["isLink"] = False
            elif is_trap:
                formatted_card["attribute"] = "TRAP"
                formatted_card["type"] = "Trap"
                formatted_card["isPendulum"] = False
                formatted_card["isLink"] = False
            else:
                # C'est une carte monstre, ajouter tous les champs
                formatted_card["attribute"] = card.get('attribute', '')
                formatted_card["atk"] = card.get('atk', 0)
                formatted_card["def"] = card.get('def', 0)
                formatted_card["level"] = card.get('level', 0)
                formatted_card["monsterType"] = card.get('race', '')
                
                # Simplifier le type de monstre
                # Vérifier d'abord les types spéciaux dans typeline
                if 'Synchro' in typeline:
                    formatted_card["type"] = "Synchro"
                elif 'Fusion' in typeline:
                    formatted_card["type"] = "Fusion"
                elif 'Xyz' in typeline:
                    formatted_card["type"] = "Xyz"
                elif 'Link' in typeline:
                    formatted_card["type"] = "Link"
                # Sinon, utiliser is_effect pour déterminer le type
                elif is_effect:
                    formatted_card["type"] = "Effect"
                else:
                    formatted_card["type"] = "Normal"
                
                formatted_card["isEffect"] = is_effect
                formatted_card["isPendulum"] = 'Pendulum' in card.get('type', '')
                formatted_card["isLink"] = 'Link' in card.get('type', '')
            
            # Gérer les archétypes
            if card.get('archetype'):
                archetype_name_en = card.get('archetype')
                formatted_card["archetype"] = archetype_name_en
                
                # Vérifier si l'archétype existe dans les fichiers
                if archetype_name_en not in existing_archetypes and archetype_name_en not in new_archetypes:
                    new_archetypes.add(archetype_name_en)
                    save_archetype_to_file(archetype_name_en, f"{name}.json")
                    created_archetype_file = True
                
            formatted_cards.append(formatted_card)
            
            # Créer l'entrée pour collection-cards
            # Chercher le set_code correspondant dans card_sets
            set_code = None
            if 'card_sets' in card:
                for card_set_info in card['card_sets']:
                    if card_set_info.get('set_name') == card_set:
                        set_code = card_set_info.get('set_code')
                        break
            
            if set_code:
                collection_card = {
                    "id": set_code,
                    "cardId": str(card.get('id', '')),
                    "collectionId": collection_id
                }
                collection_cards.append(collection_card)
        
        # Trier les cartes de collection par code (SDY-001, SDY-002, etc.)
        def extract_number(item):
            # Extraire le numéro du code (ex: SDY-001 -> 1)
            match = re.search(r'-(\d+)', item['id'])
            if match:
                return int(match.group(1))
            return 0
        
        # Trier les deux listes
        collection_cards.sort(key=extract_number)
        
        # Pour les cartes formatées, on les trie en fonction de leur position dans collection_cards
        # Créer un dictionnaire pour associer cardId à sa position dans collection_cards
        card_positions = {}
        for i, card in enumerate(collection_cards):
            card_positions[card['cardId']] = i
        
        # Trier formatted_cards en fonction de la position dans collection_cards
        def get_card_position(card):
            return card_positions.get(card['id'], 999999)  # Valeur élevée pour les cartes sans position
        
        formatted_cards.sort(key=get_card_position)
        
        # Créer le fichier cards/{name}.json
        cards_file = f"cards/{name}.json"
        os.makedirs(os.path.dirname(cards_file), exist_ok=True)
        with open(cards_file, 'w', encoding='utf-8') as file:
            json.dump(formatted_cards, file, ensure_ascii=False, indent=2)
        
        # Créer le fichier collection-cards/{name}.json
        collection_file = f"collection-cards/{name}.json"
        os.makedirs(os.path.dirname(collection_file), exist_ok=True)
        with open(collection_file, 'w', encoding='utf-8') as file:
            json.dump(collection_cards, file, ensure_ascii=False, indent=2)
        
        print(f"Fichiers créés avec succès:")
        print(f"  - {cards_file}")
        print(f"  - {collection_file}")
        print(f"  - collections/{name}.json")
        if new_archetypes:
            print(f"  - archetypes/{name}.json (nouveaux archétypes: {', '.join(new_archetypes)})")
        print(f"Nombre de cartes: {len(formatted_cards)}")
        print(f"Nombre d'entrées de collection: {len(collection_cards)}")
        
        # Mettre à jour le manifest.json
        print("\nMise à jour du manifest.json...")
        update_manifest(name, created_archetype_file)
        
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"Erreur lors de la récupération des données: {e}")
        return False
    except json.JSONDecodeError as e:
        print(f"Erreur lors du décodage JSON: {e}")
        return False
    except Exception as e:
        print(f"Erreur inattendue: {e}")
        return False

def main():
    if len(sys.argv) != 5:
        print("Usage: python fetch_card_set.py <card_set> <name> <collection_id> <code_prefix>")
        print("Exemple: python fetch_card_set.py 'Starter Deck: Yugi' sdy sdy SDY-FR")
        sys.exit(1)
    
    card_set = sys.argv[1]
    name = sys.argv[2]
    collection_id = sys.argv[3]
    code_prefix = sys.argv[4]
    
    # Récupérer les cartes et créer les fichiers
    if not fetch_card_set(card_set, name, collection_id, code_prefix):
        sys.exit(1)

if __name__ == "__main__":
    main()