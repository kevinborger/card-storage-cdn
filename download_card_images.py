#!/usr/bin/env python3
import json
import sys
import os
import requests
from PIL import Image
from io import BytesIO

def download_and_resize_image(card_id, output_dir):
    """
    Télécharge une image de carte depuis ygoprodeck et la redimensionne
    """
    # Supprimer les zéros en début d'ID pour l'URL uniquement
    clean_id_for_url = card_id.lstrip('0') or '0'
    url = f"https://images.ygoprodeck.com/images/cards/{clean_id_for_url}.jpg"
    
    # Garder l'ID complet pour le nom de fichier
    output_path = os.path.join(output_dir, f"{card_id}.jpg")
    
    try:
        # Télécharger l'image
        print(f"Téléchargement de l'image pour l'ID: {card_id} depuis URL: {clean_id_for_url}")
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        # Ouvrir l'image avec PIL
        image = Image.open(BytesIO(response.content))
        
        # Redimensionner à 60x84
        resized_image = image.resize((60, 84), Image.Resampling.LANCZOS)
        
        # Sauvegarder l'image redimensionnée
        resized_image.save(output_path, "JPEG", quality=95)
        print(f"Image sauvegardée: {output_path}")
        
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"Erreur lors du téléchargement pour l'ID {card_id}: {e}")
        return False
    except Exception as e:
        print(f"Erreur lors du traitement de l'image pour l'ID {card_id}: {e}")
        return False

def process_json_file(json_path):
    """
    Lit le fichier JSON et extrait les IDs des cartes
    """
    try:
        with open(json_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
        
        # Extraire les IDs
        card_ids = []
        if isinstance(data, list):
            for card in data:
                if 'id' in card:
                    card_ids.append(card['id'])
        elif isinstance(data, dict) and 'id' in data:
            card_ids.append(data['id'])
        
        return card_ids
        
    except FileNotFoundError:
        print(f"Erreur: Le fichier {json_path} n'existe pas.")
        return []
    except json.JSONDecodeError:
        print(f"Erreur: Le fichier {json_path} n'est pas un JSON valide.")
        return []
    except Exception as e:
        print(f"Erreur lors de la lecture du fichier: {e}")
        return []

def main():
    if len(sys.argv) != 2:
        print("Usage: python download_card_images.py <chemin_vers_fichier_json>")
        sys.exit(1)
    
    json_path = sys.argv[1]
    
    # Vérifier que le fichier existe
    if not os.path.exists(json_path):
        print(f"Erreur: Le fichier {json_path} n'existe pas.")
        sys.exit(1)
    
    # Créer le dossier cards-image s'il n'existe pas
    output_dir = "cards-image"
    os.makedirs(output_dir, exist_ok=True)
    
    # Traiter le fichier JSON
    card_ids = process_json_file(json_path)
    
    if not card_ids:
        print("Aucun ID de carte trouvé dans le fichier JSON.")
        sys.exit(1)
    
    print(f"Trouvé {len(card_ids)} carte(s) à télécharger.")
    
    # Télécharger et redimensionner les images
    success_count = 0
    for card_id in card_ids:
        if download_and_resize_image(card_id, output_dir):
            success_count += 1
    
    print(f"\nTerminé! {success_count}/{len(card_ids)} images téléchargées avec succès.")

if __name__ == "__main__":
    main()