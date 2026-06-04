# ml/recommender.py

import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from ..models import Dish, Ingredients

# Cache storage
_similarity_cache = {
    'dish_count': 0,
    'df': None,
    'tfidf_matrix': None
}

def get_dish_dataframe():
    # Use values() to avoid expensive ORM object creation
    dishes = Dish.objects.values('id', 'name', 'cuisine', 'category')
    
    # Fetch all ingredients and group them by dish_id
    ingredients = Ingredients.objects.values_list('dish_id', 'item')
    ing_dict = {}
    for dish_id, item in ingredients:
        if dish_id not in ing_dict:
            ing_dict[dish_id] = []
        ing_dict[dish_id].append(item)
    
    data = []
    for dish in dishes:
        ing_list = ing_dict.get(dish['id'], [])
        ing_text = " ".join(ing_list)
        
        # Optimize Recommendations: Weighting important features heavier
        # Repeating cuisine and category 3 times ensures the TF-IDF vectorizer prioritizes matching these tags.
        # Repeating name 2 times helps match similar dish titles.
        cuisine_weight = f"{dish['cuisine'] or ''} " * 3
        category_weight = f"{dish['category'] or ''} " * 3
        name_weight = f"{dish['name'] or ''} " * 2
        
        weighted_text = f"{name_weight} {cuisine_weight} {category_weight} {ing_text}"
        
        data.append({
            'id': dish['id'],
            'text': weighted_text
        })

    return pd.DataFrame(data)

def build_similarity_matrix():
    global _similarity_cache
    current_count = Dish.objects.count()

    # Invalidate cache if new dishes were added or removed
    if _similarity_cache['df'] is not None and _similarity_cache['dish_count'] == current_count:
        return _similarity_cache['df'], _similarity_cache['tfidf_matrix']

    df = get_dish_dataframe()
    if df.empty:
        return df, None

    # Use n-grams (1,2) to catch multi-word ingredients and phrases like "fried rice"
    # Added max_df and min_df to reduce matrix size and filter out noise
    vectorizer = TfidfVectorizer(stop_words='english', ngram_range=(1, 2), max_df=0.85, min_df=2)
    tfidf_matrix = vectorizer.fit_transform(df['text'])

    # DO NOT COMPUTE N x N cosine similarity matrix here as it consumes too much memory (O(N^2)).
    # We will compute it on-the-fly for the query only.

    # Update cache
    _similarity_cache['dish_count'] = current_count
    _similarity_cache['df'] = df
    _similarity_cache['tfidf_matrix'] = tfidf_matrix

    return df, tfidf_matrix

def get_recommendations(dish_id, top_n=5):
    df, tfidf_matrix = build_similarity_matrix()

    if tfidf_matrix is None:
        return Dish.objects.none()

    matches = df[df['id'] == dish_id]

    if matches.empty:
        return Dish.objects.none()

    idx = matches.index[0]
    query_vector = tfidf_matrix[idx]
    
    # Compute similarity only between the query vector and all other vectors
    # This returns a 1 x N matrix and is O(N) instead of O(N^2)
    scores_array = cosine_similarity(query_vector, tfidf_matrix).flatten()
    
    # Get indices of top matches
    # argsort sorts in ascending order, so we reverse it
    top_indices = np.argsort(scores_array)[::-1]
    
    # Filter out the query item itself
    top_indices = [i for i in top_indices if i != idx]
    top_indices = top_indices[:top_n]
    
    dish_ids = [df.iloc[i]['id'] for i in top_indices]

    preserved = {id: index for index, id in enumerate(dish_ids)}
    return sorted(
        Dish.objects.filter(id__in=dish_ids),
        key=lambda x: preserved.get(x.id, float('inf'))
    )