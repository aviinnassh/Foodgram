import os
import torch
from transformers import CLIPProcessor, CLIPModel
from PIL import Image
import faiss
import numpy as np
from django.conf import settings
from ..models import Dish

# Model setup
MODEL_NAME = "openai/clip-vit-large-patch14"
INDEX_PATH = os.path.join(settings.BASE_DIR, 'faiss_index.bin')
ID_MAP_PATH = os.path.join(settings.BASE_DIR, 'faiss_id_map.npy')

# Lazy load globals
_model = None
_processor = None
_index = None
_id_map = None

def get_model_and_processor():
    global _model, _processor
    if _model is None or _processor is None:
        try:
            _model = CLIPModel.from_pretrained(MODEL_NAME)
            _processor = CLIPProcessor.from_pretrained(MODEL_NAME)
            if torch.cuda.is_available():
                _model = _model.to('cuda')
            _model.eval()
        except Exception as e:
            print(f"Error loading CLIP model: {e}")
            return None, None
    return _model, _processor

def load_index():
    global _index, _id_map
    if _index is None or _id_map is None:
        if os.path.exists(INDEX_PATH) and os.path.exists(ID_MAP_PATH):
            _index = faiss.read_index(INDEX_PATH)
            _id_map = np.load(ID_MAP_PATH)
        else:
            print("FAISS index not found. Please run the build_image_index command.")
    return _index, _id_map

def get_image_embedding(image_path):
    model, processor = get_model_and_processor()
    if model is None:
        return None
        
    try:
        image = Image.open(image_path).convert("RGB")
        inputs = processor(images=image, return_tensors="pt")
        
        if torch.cuda.is_available():
            inputs = {k: v.to('cuda') for k, v in inputs.items()}
            
        with torch.no_grad():
            outputs = model.get_image_features(**inputs)
            if isinstance(outputs, torch.Tensor):
                image_features = outputs
            else:
                image_features = outputs.pooler_output if hasattr(outputs, 'pooler_output') else outputs[1]
            
        # Normalize the embeddings for cosine similarity
        image_features = image_features / image_features.norm(dim=-1, keepdim=True)
        return image_features.cpu().numpy()
    except Exception as e:
        print(f"Error processing image {image_path}: {e}")
        return None

def get_image_embeddings_batch(image_paths):
    model, processor = get_model_and_processor()
    if model is None:
        return None, []
        
    try:
        images = []
        valid_paths = []
        for path in image_paths:
            try:
                img = Image.open(path).convert("RGB")
                images.append(img)
                valid_paths.append(path)
            except Exception as e:
                print(f"Error opening image {path}: {e}")
                
        if not images:
            return None, []
            
        inputs = processor(images=images, return_tensors="pt")
        
        if torch.cuda.is_available():
            inputs = {k: v.to('cuda') for k, v in inputs.items()}
            
        with torch.no_grad():
            outputs = model.get_image_features(**inputs)
            if isinstance(outputs, torch.Tensor):
                image_features = outputs
            else:
                image_features = outputs.pooler_output if hasattr(outputs, 'pooler_output') else outputs[1]
            
        # Normalize the embeddings for cosine similarity
        image_features = image_features / image_features.norm(dim=-1, keepdim=True)
        return image_features.cpu().numpy(), valid_paths
    except Exception as e:
        print(f"Error processing image batch: {e}")
        return None, []

def get_similar_recipes_from_image(image_path, top_n=5, category_filter=None):
    """
    Given an uploaded image path, return the top N matching Dish objects using CLIP and FAISS.
    """
    index, id_map = load_index()
    if index is None or id_map is None:
        return Dish.objects.none()
        
    query_embedding = get_image_embedding(image_path)
    if query_embedding is None:
        return Dish.objects.none()
        
    # Search the FAISS index
    # faiss search expects a 2D array
    search_k = max(50, top_n * 5) if category_filter else top_n
    distances, indices = index.search(query_embedding.astype(np.float32), search_k)
    
    matched_dish_ids = []
    seen = set()
    for idx in indices[0]:
        if idx != -1:  # -1 means no match found
            dish_id = int(id_map[idx])
            if dish_id not in seen:
                matched_dish_ids.append(dish_id)
                seen.add(dish_id)
            
    if not matched_dish_ids:
        return Dish.objects.none()
        
    dishes = Dish.objects.filter(id__in=matched_dish_ids)
    
    if category_filter:
        dishes = dishes.filter(category__icontains=category_filter)
        
    # Preserve order
    preserved = {id: index for index, id in enumerate(matched_dish_ids)}
    sorted_dishes = sorted(dishes, key=lambda x: preserved.get(x.id, float('inf')))
    return sorted_dishes[:top_n]

def add_dish_to_index(dish):
    index, id_map = load_index()
    if index is None or id_map is None:
        return False
        
    if not dish.img:
        return False
        
    try:
        img_path = dish.img.path
        if not os.path.exists(img_path):
            return False
            
        embedding = get_image_embedding(img_path)
        if embedding is not None:
            index.add(embedding.astype(np.float32))
            
            global _id_map
            _id_map = np.append(id_map, dish.id)
            
            faiss.write_index(index, INDEX_PATH)
            np.save(ID_MAP_PATH, _id_map)
            return True
    except Exception as e:
        print(f"Error adding dish to index: {e}")
    return False
