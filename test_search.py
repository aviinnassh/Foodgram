import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'foodgram.settings')
django.setup()

from app.ml.image_recommender import get_similar_recipes_from_image

def main():
    test_img = 'test.jpg'
    if not os.path.exists(test_img):
        print(f"Error: {test_img} not found.")
        sys.exit(1)
        
    print(f"Testing similarity search for {test_img}...")
    dishes = get_similar_recipes_from_image(test_img, top_n=3)
    
    if not dishes:
        print("No matches found.")
        return
        
    print("\nTop Matches:")
    for dish in dishes:
        print(f"ID: {dish.id} | Name: {dish.name} | Cuisine: {dish.cuisine}")

if __name__ == '__main__':
    main()
