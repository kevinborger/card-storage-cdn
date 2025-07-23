#!/usr/bin/env python3
import json
import sys
import os
import requests
import re

def fetch_card_set(card_set, name, collection_id):
    """
    Récupère les informations des cartes d'un set spécifique depuis l'API YGOPRODeck
    et crée deux fichiers JSON : un pour les cartes et un pour la collection
    """
    # Construire l'URL de l'API
    url = f"https://db.ygoprodeck.com/api/v7/cardinfo.php?cardset={card_set}&language=fr"
    
    try:
        # Récupérer les données de l'API
        print(f"Récupération des données pour le set: {card_set}")
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        # Convertir la réponse en JSON
        api_data = response.json()
        
        # Vérifier si des cartes ont été trouvées
        if 'data' not in api_data or not api_data['data']:
            print(f"Aucune carte trouvée pour le set: {card_set}")
            return False
        
        # Transformer les données au format souhaité
        formatted_cards = []
        collection_cards = []
        
        for card in api_data['data']:
            card_type = card.get('type', '')
            is_spell = 'Spell' in card_type
            is_trap = 'Trap' in card_type
            
            # Créer la carte formatée avec les champs communs
            formatted_card = {
                "id": str(card.get('id', '')),
                "name": card.get('name', ''),
                "nameEn": card.get('name_en', card.get('name', '')),
                "description": card.get('desc', '')
            }
            
            # Gérer les cartes magie et piège
            if is_spell:
                formatted_card["attribute"] = "SPELL"
                formatted_card["type"] = "Magic"
                formatted_card["isEffect"] = False
                formatted_card["isPendulum"] = False
                formatted_card["isLink"] = False
            elif is_trap:
                formatted_card["attribute"] = "TRAP"
                formatted_card["type"] = "Trap"
                formatted_card["isEffect"] = False
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
                if 'Normal Monster' in card_type:
                    formatted_card["type"] = "Normal"
                elif 'Effect Monster' in card_type or 'Flip Effect Monster' in card_type:
                    formatted_card["type"] = "Effect"
                else:
                    formatted_card["type"] = card.get('type', '')
                
                formatted_card["isEffect"] = 'Effect' in card.get('type', '')
                formatted_card["isPendulum"] = 'Pendulum' in card.get('type', '')
                formatted_card["isLink"] = 'Link' in card.get('type', '')
            
            # Ajouter archetype uniquement s'il n'est pas vide
            if card.get('archetype'):
                formatted_card["archetype"] = card.get('archetype')
                
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
        print(f"Nombre de cartes: {len(formatted_cards)}")
        print(f"Nombre d'entrées de collection: {len(collection_cards)}")
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
    if len(sys.argv) != 4:
        print("Usage: python fetch_card_set.py <card_set> <name> <collection_id>")
        print("Exemple: python fetch_card_set.py 'Starter Deck: Yugi' sdy sdy")
        sys.exit(1)
    
    card_set = sys.argv[1]
    name = sys.argv[2]
    collection_id = sys.argv[3]
    
    # Récupérer les cartes et créer les fichiers
    if not fetch_card_set(card_set, name, collection_id):
        sys.exit(1)

if __name__ == "__main__":
    main()