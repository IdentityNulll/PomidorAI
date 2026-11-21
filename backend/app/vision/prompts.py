"""Every CLIP prompt the pipeline uses.

Split out of labels.py, which now holds only the disease vocabulary. These
are prose, not code, and they are the main thing worth tuning - but only
against the scored sets (see backend/scripts/evaluate.py), because a change
that fixes one photo routinely breaks two others.
"""

from .labels import HEALTHY

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
        "a tomato plant", "tomato plant leaves", "a ripe red tomato fruit on a plain background", ], "cotton": [
        "a cotton plant", "cotton plant leaves", "an open white cotton boll", ], "grape": [
        "a grape vine", "grape vine leaves", "a bunch of grapes on a plain background", ], "apple": [
        "an apple tree", "apple tree leaves", "a single red apple fruit on a plain background", ], "wheat": [
        "a wheat plant", "a field of wheat", "ears of wheat grain", ], "pomegranate": [
        "a pomegranate tree", "pomegranate tree leaves", "a whole pomegranate fruit on a plain background", ], "apricot": [
        "an apricot tree", "apricot tree leaves", "whole apricot fruits on a plain background", ], "potato": [
        "a potato plant", "potato plant leaves", "raw potato tubers on a plain background", ], }

# PlantNet answers with a species for literally any image, so something has
# to decide whether there is a plant in frame at all. These two prompt sets
# are that gate.
PLANT_PROMPTS = [
    "a plant", "leaves of a plant", "a tree or shrub", "a flower or flowering plant", "a crop growing in a field or garden", "grass or weeds", # Harvested produce is plant material too. Without these a market stall
    # of peppers was rejected outright as "a building or street", because
    # the stall and the shoppers behind it matched better than "a plant".
    "harvested fruit or vegetables", "produce on a market stall", "fruit or vegetables in a basket, crate or pile", ]

NOT_PLANT_PROMPTS = [
    "a person", "an animal", "a car or vehicle", "a building or street", "a computer or phone screen", "furniture or an indoor room", "a cooked meal on a plate", "a document or text on paper", "a tool or machine", ]

# The disease model was trained on single leaves against a plain background.
# On whole-plant, fruit or field photos it still returns a confident answer, # and that answer is usually wrong - so we check how leaf-like the photo is
# first and refuse to make a specific claim when it is not.
LEAF_PROMPTS = [
    "a close-up photo of a single plant leaf", "a close-up photo of plant leaves filling the frame", "a plant leaf photographed against a plain background", ]

NOT_LEAF_PROMPTS = [
    "a photo of a whole plant or tree", "a wide photo of a field or landscape", "a photo of a harvested fruit or vegetable", "a photo of flowers", "a photo of soil or ground", ]

# Binary prompts used for crops the disease model does not cover.
HEALTH_PROMPTS = {
    HEALTHY: [
        "a healthy green {plant} leaf", "a {plant} plant with no disease", ], "Kasallik belgilari bor": [
        "a diseased {plant} leaf with brown spots", "a {plant} plant with yellowing wilting damaged leaves", ], }


# --- What kind of photo is this? -------------------------------------------
#
# People photograph the hosil the harvest at least as often as the growing
# plant. The species model is trained on PlantCLEF - plants in the ground -
# and scored 0/7 on harvested produce, calling grapes "Lemna gibba"
# (duckweed) and potatoes "Salvinia molesta" (an aquatic fern). CLIP with
# produce prompts scored 7/7 on the same photos. So the pipeline first asks
# which kind of photo it has, then sends it to whichever model is competent.

VIEW_HARVEST = "hosil"
VIEW_PLANT = "o'simlik"
VIEW_LEAF = "barg"

VIEW_PROMPTS = {
    # The distinction that matters is DETACHED vs STILL GROWING, not
    # "is there fruit in the picture". A pepper plant with peppers on it is
    # a plant; peppers in a crate are hosil. Getting this wrong sent photos
    # of a growing pepper bush down the produce path and called them quince.
    VIEW_HARVEST: [
        "picked fruit in a basket or a crate",
        "vegetables laid out on a table or a plate",
        "produce for sale on a market stall",
        "a pile of harvested produce, separated from the plant",
        "cut or sliced fruit on a kitchen surface",
        "fruit and vegetables indoors, with no plant or soil around them",
    ],
    VIEW_PLANT: [
        "a plant growing in the ground",
        "fruit still growing on a tree, vine or bush",
        "a crop growing in a field",
        "a tree or shrub outdoors with branches and soil",
        "a flowering plant in a garden",
        "a plant in a pot",
        "a bare or autumn tree branch with leaves",
    ],
    VIEW_LEAF: [
        "a close-up of a single plant leaf",
        "plant leaves filling the frame",
        "a leaf held in a hand",
    ],
}

# One class per curated crop, covering EVERY view of it: growing plant, leaf,
# and harvested produce. A farmer photographs whichever is in front of them,
# and a single class per crop means the answer does not depend on guessing
# the view correctly first.
#
# Each entry is a plants.json id.
CROP_OTHER = "__other__"

CROP_PROMPTS = {
    "tomato": [
        "a tomato plant with round red or green tomatoes",
        "tomato plant leaves",
        "ripe red tomatoes picked",
    ],
    "pepper": [
        "a pepper plant with a long green bell pepper hanging from it",
        "a capsicum pepper fruit growing on a bush",
        "pepper plant leaves",
        "picked bell peppers",
    ],
    "grape": [
        "a grape vine with bunches of grapes",
        "grape vine leaves",
        "picked bunches of grapes",
    ],
    "apple": ["an apple tree with apples on it", "apple tree leaves", "picked apples"],
    "quince": [
        "a quince tree with quince fruit on it",
        "quince tree leaves",
        "picked quince fruit",
    ],
    "pomegranate": [
        "a pomegranate tree with fruit",
        "pomegranate leaves",
        "picked pomegranates",
    ],
    "apricot": ["an apricot tree with apricots", "apricot tree leaves", "picked apricots"],
    "potato": [
        "a potato plant growing in a field",
        "potato plant leaves",
        "harvested potato tubers",
    ],
    "wheat": ["a wheat field", "wheat plant leaves", "wheat grain"],
    "cotton": ["a cotton plant with bolls", "cotton plant leaves", "harvested raw cotton"],
    "maize": ["a maize plant growing", "maize plant leaves", "corn on the cob"],
    "cucumber": [
        "a cucumber plant with cucumbers",
        "cucumber plant leaves",
        "picked cucumbers",
    ],
    "onion": ["onion plants growing in soil", "onion green tops", "dry onion bulbs"],
    "carrot": ["carrot plants growing in soil", "carrot leafy tops", "harvested carrots"],
    "beet": [
        "a beet plant with broad dark green leaves and red stems",
        "beetroot leaves",
        "harvested beetroots",
    ],
    "coriander": ["a coriander plant growing", "coriander leaves", "fresh coriander bunch"],
    "dill": ["a dill plant growing", "feathery dill leaves", "fresh dill bunch"],
    "cherry": ["a cherry tree with cherries", "cherry tree leaves", "picked cherries"],
    "peach": ["a peach tree with peaches", "peach tree leaves", "picked peaches"],
    "strawberry": [
        "a strawberry plant with berries",
        "strawberry leaves",
        "picked strawberries",
    ],
    "rose": ["a rose bush with roses", "rose leaves", "cut roses"],
    "chrysanthemum": [
        "a chrysanthemum plant with flowers",
        "chrysanthemum leaves",
        "cut chrysanthemums",
    ],
    # Softmax must pick something. Without this, every weed and wildflower
    # gets forced into the nearest crop - the original bug in this app.
    CROP_OTHER: [
        "a wild plant that is not a crop",
        "a weed",
        "an ornamental tree",
        "grass",
        "a houseplant",
        "a wildflower",
        "moss or fern",
        "a cooked meal",
        "a person or animal",
        "a building or vehicle",
    ],
}
