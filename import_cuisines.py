import os
import django
import pandas as pd
import shutil
import re

# Setup Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "foodgram.settings")
django.setup()

from app.models import Dish, Ingredients, Cooking
from django.contrib.auth.models import User
from django.conf import settings
from django.db import transaction

def import_cuisines(csv_path, img_dir):
    user, created = User.objects.get_or_create(username='admin', defaults={
        'first_name': 'Admin',
        'email': 'admin@foodgram.com'
    })

    print(f"Reading dataset from {csv_path}...")
    try:
        df = pd.read_csv(csv_path)
        
        # Optionally, clear old recipes if needed. The user didn't specify to delete old recipes,
        # but in previous conversations we did. I'll just append them to be safe, or just clear them.
        # Actually, let's keep existing recipes and just add the new ones, or delete and add?
        # "add the data set with the image cuisines.csv" implies adding to the existing ones.
        # Let's just add them.

        img_files = os.listdir(img_dir)
        # Create a mapping from url filename to actual file in data/
        # e.g., url is "https://.../Thayir_Curd_Semiya...-4.jpg" -> "Thayir_Curd_Semiya...-4.jpg"
        # files are "1.Thayir_Curd_Semiya...-4.jpg"
        file_map = {}
        for f in img_files:
            parts = f.split('.', 1)
            if len(parts) == 2:
                file_map[parts[1]] = f
            file_map[f] = f

        count = 0
        ingredients_to_create = []
        cooking_to_create = []
        
        with transaction.atomic():
            for index, row in df.iterrows():
                name = row.get('name', 'Unnamed Recipe')
                try:
                    name_ascii = name.encode('ascii', 'ignore').decode('ascii')
                    print(f"Importing recipe: {name_ascii}")
                except Exception:
                    pass
                
                prep_time_str = str(row.get('prep_time', ''))
                # Try to extract minutes from 'Total in 35 M'
                minutes = 30
                m = re.search(r'(\d+)', prep_time_str)
                if m:
                    minutes = int(m.group(1))
                    
                prep_mins = minutes // 3
                cook_mins = minutes - prep_mins
                
                dish = Dish.objects.create(
                    user=user,
                    name=name,
                    cuisine=row.get('cuisine', 'Various'),
                    category=row.get('course', 'Various'),
                    prep=prep_mins,
                    cook=cook_mins,
                    likes=0
                )
                
                # Handle Image
                image_url = row.get('image_url')
                if pd.notna(image_url):
                    url_filename = str(image_url).split('/')[-1]
                    local_file = file_map.get(url_filename)
                    if local_file:
                        src_path = os.path.join(img_dir, local_file)
                        dest_filename = f"recipe_{dish.id}_{local_file}"
                        dest_path = os.path.join(settings.MEDIA_ROOT, dest_filename)
                        shutil.copy(src_path, dest_path)
                        dish.img.name = dest_filename
                        dish.save()
                    else:
                        try:
                            print(f"  - Could not find local image for: {url_filename.encode('ascii', 'ignore').decode('ascii')}")
                        except: pass
                
                # Handle Ingredients
                ingredients_str = str(row.get('ingredients', ''))
                lines = [line.strip() for line in ingredients_str.split('\n') if line.strip()]
                
                for line in lines:
                    line = re.sub(r'\s+', ' ', line).strip()
                    if line and not line.lower().startswith('for ') and line != ',':
                        ingredients_to_create.append(Ingredients(dish=dish, item=line))
                
                # Handle Instructions
                instructions_str = str(row.get('instructions', ''))
                if instructions_str and instructions_str.lower() != 'nan':
                    cooking_to_create.append(Cooking(dish=dish, steps=instructions_str))
                    
                # Batch save
                if len(ingredients_to_create) > 5000:
                    Ingredients.objects.bulk_create(ingredients_to_create)
                    ingredients_to_create = []
                
                if len(cooking_to_create) > 1000:
                    Cooking.objects.bulk_create(cooking_to_create)
                    cooking_to_create = []
                    
                count += 1
                
            # Create any remaining objects
            if ingredients_to_create:
                Ingredients.objects.bulk_create(ingredients_to_create)
            if cooking_to_create:
                Cooking.objects.bulk_create(cooking_to_create)
                
        print(f"Successfully imported {count} recipes with images!")

    except FileNotFoundError:
        print(f"Error: Could not find {csv_path} or image directory.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    csv_file_name = r"d:\main project\foodgram\foodgram\cuisines.csv"
    img_directory = r"d:\main project\foodgram\foodgram\image_for _cuisines\data"
    import_cuisines(csv_file_name, img_directory)
