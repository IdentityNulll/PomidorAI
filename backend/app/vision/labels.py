"""Mapping from model label spaces into the app's Uzbek vocabulary.

The disease model (kimcomehome/plantvillage-vit-leaf-disease) is trained on
PlantVillage and emits 38 English `Crop___Disease` labels.

NOTE: the Uzbek disease names below are translations written without
agronomist review, same caveat as data/plants.json. Have them checked before
the app is used for real advice.
"""

HEALTHY = "Sog'lom"
HEALTHY_SLUG = "soglom"

# plants.json id -> the crop prefix used by the PlantVillage label space.
# All 14 crops the disease model was trained on. Anything outside this set
# gets the weaker CLIP healthy-vs-diseased fallback instead.
CROP_BY_PLANT_ID = {
    "tomato": "Tomato",
    "potato": "Potato",
    "apple": "Apple",
    "grape": "Grape",
    "pepper": "Pepper,_bell",
    "maize": "Corn_(maize)",
    "cherry": "Cherry_(including_sour)",
    "peach": "Peach",
    "strawberry": "Strawberry",
    "squash": "Squash",
    "orange": "Orange",
    "soybean": "Soybean",
    "blueberry": "Blueberry",
    "raspberry": "Raspberry",
}

# Exact PlantVillage label -> a key in data/diseases.json, which holds the
# Uzbek name plus what it looks like, why it happens and what to do about it.
# Keys must match the model config verbatim.
#
# Several labels share a slug on purpose: "Black rot" on an apple and on a
# grape is the same disease to the farmer holding the phone.
DISEASE_SLUG = {
    "Apple___Apple_scab": "olma-qotiri",
    "Apple___Black_rot": "qora-chirish",
    "Apple___Cedar_apple_rust": "olma-zangi",
    "Apple___healthy": HEALTHY_SLUG,
    "Grape___Black_rot": "qora-chirish",
    "Grape___Esca_(Black_Measles)": "eska",
    "Grape___Leaf_blight_(Isariopsis_Leaf_Spot)": "barg-kuyishi",
    "Grape___healthy": HEALTHY_SLUG,
    "Potato___Early_blight": "alternarioz",
    "Potato___Late_blight": "fitoftoroz",
    "Potato___healthy": HEALTHY_SLUG,
    "Tomato___Bacterial_spot": "bakterial-doglanish",
    "Tomato___Early_blight": "alternarioz",
    "Tomato___Late_blight": "fitoftoroz",
    "Tomato___Leaf_Mold": "barg-mogori",
    "Tomato___Septoria_leaf_spot": "septorioz",
    "Tomato___Spider_mites Two-spotted_spider_mite": "orgimchakkana",
    "Tomato___Target_Spot": "nishonsimon-dog",
    "Tomato___Tomato_Yellow_Leaf_Curl_Virus": "sariq-barg-burishish",
    "Tomato___Tomato_mosaic_virus": "mozaika",
    "Tomato___healthy": HEALTHY_SLUG,
    "Pepper,_bell___Bacterial_spot": "bakterial-doglanish",
    "Pepper,_bell___healthy": HEALTHY_SLUG,
    "Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot": "serkosporoz",
    "Corn_(maize)___Common_rust_": "zang",
    "Corn_(maize)___Northern_Leaf_Blight": "shimoliy-barg-kuyishi",
    "Corn_(maize)___healthy": HEALTHY_SLUG,
    "Cherry_(including_sour)___Powdery_mildew": "un-shudring",
    "Cherry_(including_sour)___healthy": HEALTHY_SLUG,
    "Peach___Bacterial_spot": "bakterial-doglanish",
    "Peach___healthy": HEALTHY_SLUG,
    "Strawberry___Leaf_scorch": "barg-kuyishi",
    "Strawberry___healthy": HEALTHY_SLUG,
    "Squash___Powdery_mildew": "un-shudring",
    "Orange___Haunglongbing_(Citrus_greening)": "sitrus-kokarishi",
    "Blueberry___healthy": HEALTHY_SLUG,
    "Raspberry___healthy": HEALTHY_SLUG,
    "Soybean___healthy": HEALTHY_SLUG,
}

