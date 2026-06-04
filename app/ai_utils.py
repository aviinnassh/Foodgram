import torch
from torchvision import models, transforms
from PIL import Image
import os
from django.conf import settings

# Load the pretrained model and set to evaluation mode
# Note: In a production environment, you might load this once globally
try:
    weights = models.MobileNet_V2_Weights.DEFAULT
    model = models.mobilenet_v2(weights=weights)
    model.eval()

    # Create the preprocessing pipeline
    preprocess = transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])

    # Load ImageNet class labels
    classes_path = os.path.join(settings.BASE_DIR, 'app', 'imagenet_classes.txt')
    with open(classes_path, 'r') as f:
        categories = [s.strip() for s in f.readlines()]
except Exception as e:
    print(f"Warning: Failed to load AI model. {e}")
    model = None
    categories = []

def analyze_food_image(image_path):
    """
    Analyzes an image and returns the top predicted food/object name.
    """
    if model is None:
        return "Unknown"
        
    try:
        input_image = Image.open(image_path)
        
        # Convert RGBA to RGB if needed
        if input_image.mode != "RGB":
            input_image = input_image.convert("RGB")
            
        input_tensor = preprocess(input_image)
        input_batch = input_tensor.unsqueeze(0) # create a mini-batch as expected by the model
        
        # Move the input and model to GPU for speed if available
        if torch.cuda.is_available():
            input_batch = input_batch.to('cuda')
            model.to('cuda')
            
        with torch.no_grad():
            output = model(input_batch)
            
        # Tensor of shape 1000, with confidence scores over Imagenet's 1000 classes
        probabilities = torch.nn.functional.softmax(output[0], dim=0)
        
        # Get top 1 prediction
        top_prob, top_catid = torch.topk(probabilities, 1)
        predicted_class = categories[top_catid[0]]
        
        # Clean up the class name (e.g., 'pizza, pizzeria' -> 'pizza')
        clean_name = predicted_class.split(',')[0].strip()
        return clean_name
        
    except Exception as e:
        print(f"Error analyzing image: {e}")
        return "Error"
