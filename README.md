# 🍽️ Foodgram

**Foodgram** is a modern, dynamic, and fully-featured social platform designed specifically for food lovers, home cooks, and professional chefs. Discover new recipes, share your culinary creations, and connect with a vibrant community of food enthusiasts. Powered by AI, Foodgram also offers personalized recipe recommendations and image-based search capabilities.

---

## ✨ Features

### 🧑‍🍳 Social Culinary Experience
* **User Profiles**: Customize your bio and profile picture to build your culinary brand.
* **Follow System**: Follow your favorite chefs and friends to curate your personalized feed.
* **Notifications**: Get real-time updates when someone follows you, likes your dish, or interacts with your profile.

### 🍳 Recipe Management
* **Upload Dishes**: Share your recipes complete with high-quality images, prep time, cook time, categories, and cuisines.
* **Step-by-Step Instructions & Ingredients**: Break down your recipes into easy-to-follow steps and ingredient lists.
* **Save for Later**: Bookmark your favorite dishes to your personal cookbook for easy access later.
* **Ratings & Likes**: Engage with the community by liking and rating the dishes you try.

### 🤖 AI-Powered Discoverability
* **Smart Recommendations**: Utilizing advanced Machine Learning (FAISS), Foodgram recommends dishes tailored to your tastes.
* **Image Recognition**: Integrated computer vision models (ImageNet) can analyze and categorize food images to enhance searchability and recommendations.

### 🛡️ Moderation & Administration
* **Reporting System**: Users can report inappropriate content to keep the community safe and focused on food.
* **Admin Dashboard**: Comprehensive moderation tools to manage users, dishes, and reports.

---

## 🚀 Tech Stack

* **Backend Framework:** Django (Python)
* **Database:** SQLite (Development)
* **Machine Learning:** FAISS (Facebook AI Similarity Search), OpenCV / PIL for Image Processing
* **Frontend:** HTML5, CSS3 (Modern, responsive UI), Vanilla JavaScript
* **Architecture:** MVT (Model-View-Template)

---

## 🛠️ Setup Instructions

To get Foodgram running on your local machine, follow these steps:

### 1. Clone the Repository
```bash
git clone https://github.com/aviinnassh/foodgram.git
cd foodgram
```

### 2. Create a Virtual Environment
It is recommended to use a virtual environment to manage dependencies.
```bash
python -m venv venv
```

### 3. Activate the Virtual Environment
* **Windows:**
  ```bash
  venv\Scripts\activate
  ```
* **Mac/Linux:**
  ```bash
  source venv/bin/activate
  ```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

### 5. Setup the Database
Run migrations to create the database schema.
```bash
python manage.py migrate
```

### 6. Run the Development Server
```bash
python manage.py runserver
```

Open your web browser and navigate to `http://127.0.0.1:8000/` to start exploring Foodgram!

---
*Developed by [aviinnassh](https://github.com/aviinnassh)*
