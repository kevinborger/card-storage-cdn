#!/usr/bin/env python3
import sys
import os
import requests
from PIL import Image
from io import BytesIO

def download_and_resize_collection_image(card_id, image_url):
    """
    Télécharge une image depuis une URL donnée et la redimensionne pour les collections
    """
    # Dossier de destination
    output_dir = "collections-image"
    os.makedirs(output_dir, exist_ok=True)
    
    # Chemin de sortie avec l'ID fourni
    output_path = os.path.join(output_dir, f"{card_id}.jpg")
    
    try:
        # Télécharger l'image
        print(f"Téléchargement de l'image pour l'ID: {card_id} depuis URL: {image_url}")
        response = requests.get(image_url, timeout=30)
        response.raise_for_status()
        
        # Ouvrir l'image avec PIL
        image = Image.open(BytesIO(response.content))
        
        # Convertir en RGB si l'image a un canal alpha (RGBA)
        if image.mode in ('RGBA', 'LA', 'P'):
            # Créer un fond blanc pour remplacer la transparence
            background = Image.new('RGB', image.size, (255, 255, 255))
            if image.mode == 'P':
                image = image.convert('RGBA')
            background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
            image = background
        elif image.mode != 'RGB':
            image = image.convert('RGB')
        
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

def main():
    if len(sys.argv) != 3:
        print("Usage: python download_collection_image.py <id> <url>")
        print("Exemple: python download_collection_image.py 12345 https://example.com/image.jpg")
        sys.exit(1)
    
    card_id = sys.argv[1]
    image_url = sys.argv[2]
    
    # Télécharger et redimensionner l'image
    if download_and_resize_collection_image(card_id, image_url):
        print(f"\nSuccès! Image téléchargée et redimensionnée pour l'ID: {card_id}")
    else:
        print(f"\nÉchec du téléchargement pour l'ID: {card_id}")
        sys.exit(1)

if __name__ == "__main__":
    main()