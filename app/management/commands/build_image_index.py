from django.core.management.base import BaseCommand
from app.models import Dish
from app.ml.image_recommender import get_model_and_processor, get_image_embeddings_batch, INDEX_PATH, ID_MAP_PATH
import faiss
import numpy as np
import os

class Command(BaseCommand):
    help = 'Builds the FAISS index for all Dish images using CLIP embeddings in batches'

    def handle(self, *args, **options):
        self.stdout.write('Loading CLIP model...')
        model, processor = get_model_and_processor()
        
        if model is None:
            self.stdout.write(self.style.ERROR('Failed to load CLIP model. Cannot build index.'))
            return
            
        dishes = Dish.objects.exclude(img='').exclude(img__isnull=True)
        total_dishes = dishes.count()
        
        if total_dishes == 0:
            self.stdout.write(self.style.WARNING('No dishes with images found.'))
            return
            
        self.stdout.write(f'Found {total_dishes} dishes with images. Generating embeddings...')
        
        # Determine embedding dimension from model configuration
        d = model.config.projection_dim
        
        # Initialize FAISS index using Inner Product (cosine similarity since embeddings are normalized)
        index = faiss.IndexFlatIP(d)
        id_map = []
        
        success_count = 0
        batch_size = 32
        
        # We need to process in chunks
        dish_batch = []
        path_batch = []
        
        for i, dish in enumerate(dishes):
            try:
                img_path = dish.img.path
                if not os.path.exists(img_path):
                    self.stdout.write(self.style.WARNING(f'Image file not found for dish {dish.id}: {img_path}'))
                    continue
                
                dish_batch.append(dish)
                path_batch.append(img_path)
                
                if len(dish_batch) >= batch_size:
                    self.stdout.write(f'Processing batch up to {i+1}/{total_dishes}...')
                    embeddings, valid_paths = get_image_embeddings_batch(path_batch)
                    
                    if embeddings is not None and len(embeddings) > 0:
                        # Map back the valid paths to dishes
                        # Note: valid_paths are the ones successfully opened
                        valid_path_set = set(valid_paths)
                        for b_dish, b_path in zip(dish_batch, path_batch):
                            if b_path in valid_path_set:
                                id_map.append(b_dish.id)
                        
                        index.add(embeddings.astype(np.float32))
                        success_count += len(embeddings)
                    
                    dish_batch = []
                    path_batch = []
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error queuing dish {dish.id}: {e}'))
                
        # Process remaining
        if len(dish_batch) > 0:
            self.stdout.write(f'Processing final batch...')
            embeddings, valid_paths = get_image_embeddings_batch(path_batch)
            if embeddings is not None and len(embeddings) > 0:
                valid_path_set = set(valid_paths)
                for b_dish, b_path in zip(dish_batch, path_batch):
                    if b_path in valid_path_set:
                        id_map.append(b_dish.id)
                index.add(embeddings.astype(np.float32))
                success_count += len(embeddings)
                
        self.stdout.write(f'Successfully generated {success_count} embeddings.')
        
        if success_count > 0:
            self.stdout.write('Saving FAISS index...')
            faiss.write_index(index, INDEX_PATH)
            np.save(ID_MAP_PATH, np.array(id_map))
            self.stdout.write(self.style.SUCCESS(f'Successfully saved FAISS index to {INDEX_PATH}'))
            self.stdout.write(self.style.SUCCESS(f'Successfully saved ID map to {ID_MAP_PATH}'))
        else:
            self.stdout.write(self.style.ERROR('No embeddings generated. Index not saved.'))
