def build_lora_xl(lora, prompt, lora_weight):
    existing_lora = False
    if lora == "3drenderstyle":
        if lora_weight == "":
            lora_weight = "1"
        prompt = "3d style, 3d render, " + prompt + " <lora:3d_render_style_xl:"+lora_weight+">"
        existing_lora = True

    if lora == "psychedelicnoir":
        if lora_weight == "":
            lora_weight = "1"
        prompt = prompt + " <lora:Psychedelic_Noir__sdxl:"+lora_weight+">>"
        existing_lora = True

    if lora == "wojak":
        if lora_weight == "":
            lora_weight = "1"
        prompt = "<lora:wojak_big:"+lora_weight+">, " + prompt + ", wojak"
        existing_lora = True

    if lora == "dreamarts":
        if lora_weight == "":
            lora_weight = "1"
        prompt = "<lora:DreamARTSDXL:"+lora_weight+">, " + prompt
        existing_lora = True

    if lora == "voxel":
        if lora_weight == "":
            lora_weight = "1"
        prompt = "voxel style, " + prompt + " <lora:last:"+lora_weight+">"
        existing_lora = True

    if lora == "kru3ger":
        if lora_weight == "":
            lora_weight = "1"
        prompt = "kru3ger_style, " + prompt + "<lora:sebastiankrueger-kru3ger_style-000007:"+lora_weight+">"
        existing_lora = True

    if lora == "inkpunk":
        if lora_weight == "":
            lora_weight = "0.5"
        prompt = "inkpunk style, " + prompt + "  <lora:IPXL_v2:"+lora_weight+">"
        existing_lora = True

    if lora == "inkscenery":
        if lora_weight == "":
            lora_weight = "1"
        prompt = " ink scenery, " + prompt + " <lora:ink_scenery_xl:"+lora_weight+">"
        existing_lora = True

    if lora == "inkpainting":
        if lora_weight == "":
            lora_weight = "0.7"
        prompt = "painting style, " +  prompt + " <lora:Ink_Painting-000006::"+lora_weight+">,"
        existing_lora = True

    if lora == "timburton":
        if lora_weight == "":
            lora_weight = "1.27"
            pencil_weight = "1.15"
        prompt = prompt + " (hand drawn with pencil"+pencil_weight+"), (tim burton style:"+lora_weight+")" 
        existing_lora = True

    if lora == "pixelart":
        if lora_weight == "":
            lora_weight = "1"
        prompt = prompt + " (flat shading:1.2), (minimalist:1.4), <lora:pixelbuildings128-v2:"+lora_weight+"> "
        existing_lora = True

    if lora == "pepe":
        if lora_weight == "":
            lora_weight = "0.8"
        prompt = prompt + " ,<lora:DD-pepe-v2:"+lora_weight+"> pepe"
        existing_lora = True

    if lora == "bettertext":
        if lora_weight == "":
            lora_weight = "1"
        prompt = prompt + " ,<lora:BetterTextRedmond:"+lora_weight+">"
        existing_lora = True

    if lora == "mspaint":
        if lora_weight == "":
            lora_weight = "1"
        prompt = "MSPaint drawing " + prompt +">"
        existing_lora = True

    if lora == "woodfigure":
        if lora_weight == "":
            lora_weight = "0.7"
        prompt = prompt + ",woodfigurez,artistic style <lora:woodfigurez-sdxl:"+lora_weight+">"
        existing_lora = True

    if lora == "fireelement":
        prompt = prompt + ",composed of fire elements, fire element"
        existing_lora = True



    return lora, prompt, existing_lora