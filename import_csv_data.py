import os
import django
import pandas as pd

# Setup Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "foodgram.settings")
django.setup()

from django.conf import settings
from app.models import Dish, Ingredients, Cooking
from django.contrib.auth.models import User
from django.db import transaction

def import_new_datasets(limit=100):
    user, created = User.objects.get_or_create(username='admin', defaults={
        'first_name': 'Admin',
        'email': 'admin@foodgram.com'
    })

    base_path = r"d:\main project\foodgram"
    recipes_csv = os.path.join(base_path, "recipes_master.csv")
    ingredients_csv = os.path.join(base_path, "recipe_ingredients.csv")
    steps_csv = os.path.join(base_path, "recipe_steps.csv")
    
    print("Reading CSV files...")
    try:
        df_recipes = pd.read_csv(recipes_csv)
        df_ingredients = pd.read_csv(ingredients_csv)
        df_steps = pd.read_csv(steps_csv)
    except Exception as e:
        print(f"Error reading CSV files: {e}")
        return

    # Limit the number of imported recipes if specified
    if limit:
        df_recipes = df_recipes.head(limit)
    
    print("Clearing old imported recipes (only from admin user)...")
    Dish.objects.filter(user=user).delete()
    
    print("Grouping ingredients and steps...")
    ingredients_grouped = df_ingredients.groupby('recipe_id')
    steps_grouped = df_steps.groupby('recipe_id')

    print(f"Importing {len(df_recipes)} recipes...")
    
    ingredients_to_create = []
    cooking_to_create = []
    
    with transaction.atomic():
        for index, row in df_recipes.iterrows():
            recipe_id = row['recipe_id']
            name = row.get('recipe_name', 'Unknown Recipe')
            
            print(f"Importing recipe: {name} ({recipe_id})")
            
            # Map category
            meal_type = str(row.get('meal_type', 'Various'))
            if meal_type == 'Dessert':
                category = 'Desserts'
            elif meal_type in ['Breakfast', 'Lunch', 'Dinner']:
                category = meal_type
            else:
                category = 'Various'
                
            calories = int(row.get('calories_per_serving', 1000)) if pd.notna(row.get('calories_per_serving')) else 1000
            if calories < 300 and category == 'Various':
                category = 'Healthy'

            # Create Dish
            dish = Dish.objects.create(
                user=user,
                name=name,
                cuisine=row.get('cuisine', 'Various'),
                category=category,
                prep=int(row.get('prep_time_minutes', 0)),
                cook=int(row.get('cook_time_minutes', 0)),
                likes=int(row.get('rating', 0) * 10) if pd.notna(row.get('rating')) else 0
            )
            
            # Get a list of existing recipe images in the media directory
            media_dir = os.path.join(settings.MEDIA_ROOT)
            existing_images = [f for f in os.listdir(media_dir) if f.startswith('recipe_') and f.endswith('.jpg')]
            
            if existing_images:
                import random
                random_image = random.choice(existing_images)
                dish.img.name = random_image
            else:
                dish.img.name = 'profile_pics/profile.jpg'
            
            dish.save()
            
            # Import Ingredients
            if recipe_id in ingredients_grouped.groups:
                recipe_ings = ingredients_grouped.get_group(recipe_id)
                for _, ing_row in recipe_ings.iterrows():
                    qty = str(ing_row.get('quantity', '')).strip()
                    item_name = str(ing_row.get('ingredient_name', '')).strip()
                    if qty and qty.lower() != 'nan':
                        item_text = f"{qty} {item_name}"
                    else:
                        item_text = item_name
                    ingredients_to_create.append(Ingredients(dish=dish, item=item_text))
                    
            # Import Steps
            if recipe_id in steps_grouped.groups:
                recipe_stps = steps_grouped.get_group(recipe_id)
                recipe_stps = recipe_stps.sort_values(by='step_number')
                steps_list = []
                for _, step_row in recipe_stps.iterrows():
                    step_num = step_row.get('step_number', '')
                    step_desc = str(step_row.get('step_description', '')).strip()
                    steps_list.append(f"{step_num}. {step_desc}")
                formatted_steps = " ".join(steps_list)
                cooking_to_create.append(Cooking(dish=dish, steps=formatted_steps))

            # Batch create every 1000 dishes to save memory
            if len(ingredients_to_create) > 5000:
                Ingredients.objects.bulk_create(ingredients_to_create)
                ingredients_to_create = []
                
            if len(cooking_to_create) > 1000:
                Cooking.objects.bulk_create(cooking_to_create)
                cooking_to_create = []

        # Create any remaining objects
        if ingredients_to_create:
            Ingredients.objects.bulk_create(ingredients_to_create)
        if cooking_to_create:
            Cooking.objects.bulk_create(cooking_to_create)

    print("Successfully imported datasets!")

if __name__ == "__main__":
    # Import the first 100 recipes. Change limit to None to import all 10,000 recipes.
    import_new_datasets(limit=100)
