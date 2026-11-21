"""Mapping from model label spaces into the app's Uzbek vocabulary.

The disease model (kimcomehome/plantvillage-vit-leaf-disease) is trained on
PlantVillage and emits 38 English `Crop___Disease` labels.

NOTE: the Uzbek disease names below are translations written without
agronomist review, same caveat as data/plants.json. Have them checked before
the app is used for real advice.
"""

HEALTHY = "Sog'lom"

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

# Exact PlantVillage label -> Uzbek. Keys must match the model config verbatim.
DISEASE_UZ = {
    "Apple___Apple_scab": "Olma qo'tiri",
    "Apple___Black_rot": "Qora chirish",
    "Apple___Cedar_apple_rust": "Olma zangi",
    "Apple___healthy": HEALTHY,
    "Grape___Black_rot": "Qora chirish",
    "Grape___Esca_(Black_Measles)": "Eska (qora o'lat)",
    "Grape___Leaf_blight_(Isariopsis_Leaf_Spot)": "Barg kuyishi",
    "Grape___healthy": HEALTHY,
    "Potato___Early_blight": "Alternarioz (erta kuyish)",
    "Potato___Late_blight": "Fitoftoroz (kech kuyish)",
    "Potato___healthy": HEALTHY,
    "Tomato___Bacterial_spot": "Bakterial dog'lanish",
    "Tomato___Early_blight": "Alternarioz (erta kuyish)",
    "Tomato___Late_blight": "Fitoftoroz (kech kuyish)",
    "Tomato___Leaf_Mold": "Barg mog'ori",
    "Tomato___Septoria_leaf_spot": "Septorioz",
    "Tomato___Spider_mites Two-spotted_spider_mite": "O'rgimchakkana",
    "Tomato___Target_Spot": "Nishonsimon dog'",
    "Tomato___Tomato_Yellow_Leaf_Curl_Virus": "Sariq barg burishish virusi",
    "Tomato___Tomato_mosaic_virus": "Tamaki mozaikasi virusi",
    "Tomato___healthy": HEALTHY,
    "Pepper,_bell___Bacterial_spot": "Bakterial dog'lanish",
    "Pepper,_bell___healthy": HEALTHY,
    "Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot": "Serkosporoz (kulrang dog')",
    "Corn_(maize)___Common_rust_": "Zang kasalligi",
    "Corn_(maize)___Northern_Leaf_Blight": "Shimoliy barg kuyishi",
    "Corn_(maize)___healthy": HEALTHY,
    "Cherry_(including_sour)___Powdery_mildew": "Un-shudring",
    "Cherry_(including_sour)___healthy": HEALTHY,
    "Peach___Bacterial_spot": "Bakterial dog'lanish",
    "Peach___healthy": HEALTHY,
    "Strawberry___Leaf_scorch": "Barg kuyishi",
    "Strawberry___healthy": HEALTHY,
    "Squash___Powdery_mildew": "Un-shudring",
    "Orange___Haunglongbing_(Citrus_greening)": "Sitrus ko'karishi (HLB)",
    "Blueberry___healthy": HEALTHY,
    "Raspberry___healthy": HEALTHY,
    "Soybean___healthy": HEALTHY,
}
