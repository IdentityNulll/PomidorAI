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

# English CLIP prompts per plants.json id. CLIP is English-trained, so the
# Uzbek names in plants.json cannot be used as prompts directly.
#
# Keep these BALANCED across crops: every crop gets a whole-plant prompt, a
# leaf prompt and a bare-fruit/product prompt. An asymmetry here shows up as a
# systematic error - while building this, tomato had a bare-fruit prompt and
# apple did not, and a studio photo of a red apple was confidently called a
# tomato.
SPECIES_PROMPTS = {
    "tomato": [
        "a tomato plant",
        "tomato plant leaves",
        "a ripe red tomato fruit on a plain background",
    ],
    "cotton": [
        "a cotton plant",
        "cotton plant leaves",
        "an open white cotton boll",
    ],
    "grape": [
        "a grape vine",
        "grape vine leaves",
        "a bunch of grapes on a plain background",
    ],
    "apple": [
        "an apple tree",
        "apple tree leaves",
        "a single red apple fruit on a plain background",
    ],
    "wheat": [
        "a wheat plant",
        "a field of wheat",
        "ears of wheat grain",
    ],
    "pomegranate": [
        "a pomegranate tree",
        "pomegranate tree leaves",
        "a whole pomegranate fruit on a plain background",
    ],
    "apricot": [
        "an apricot tree",
        "apricot tree leaves",
        "whole apricot fruits on a plain background",
    ],
    "potato": [
        "a potato plant",
        "potato plant leaves",
        "raw potato tubers on a plain background",
    ],
}

# PlantNet answers with a species for literally any image, so something has
# to decide whether there is a plant in frame at all. These two prompt sets
# are that gate.
PLANT_PROMPTS = [
    "a plant",
    "leaves of a plant",
    "a tree or shrub",
    "a flower or flowering plant",
    "a crop growing in a field or garden",
    "grass or weeds",
]

NOT_PLANT_PROMPTS = [
    "a person",
    "an animal",
    "a car or vehicle",
    "a building or street",
    "a computer or phone screen",
    "furniture or an indoor room",
    "a cooked meal on a plate",
    "a document or text on paper",
    "a tool or machine",
]

# The disease model was trained on single leaves against a plain background.
# On whole-plant, fruit or field photos it still returns a confident answer,
# and that answer is usually wrong - so we check how leaf-like the photo is
# first and refuse to make a specific claim when it is not.
LEAF_PROMPTS = [
    "a close-up photo of a single plant leaf",
    "a close-up photo of plant leaves filling the frame",
    "a plant leaf photographed against a plain background",
]

NOT_LEAF_PROMPTS = [
    "a photo of a whole plant or tree",
    "a wide photo of a field or landscape",
    "a photo of a harvested fruit or vegetable",
    "a photo of flowers",
    "a photo of soil or ground",
]

# Binary prompts used for crops the disease model does not cover.
HEALTH_PROMPTS = {
    HEALTHY: [
        "a healthy green {plant} leaf",
        "a {plant} plant with no disease",
    ],
    "Kasallik belgilari bor": [
        "a diseased {plant} leaf with brown spots",
        "a {plant} plant with yellowing wilting damaged leaves",
    ],
}
