
#We can add multiple Tasks here and call them in the do_work function.

#Also make sure to define your task in  get supported tasks, and in get amount per task and listen to
#the according event type in the beginning of dvm.py and


def GoogleTranslate(text, translation_lang):
    from translatepy.translators.google import GoogleTranslate
    gtranslate = GoogleTranslate()
    length = len(text)

    step = 0
    translated_text = ""
    if length > 4999:
        while step+5000 < length:
            textpart = text[step:step+5000]
            step = step + 5000
            try:
                translated_text_part = str(gtranslate.translate(textpart, translation_lang))
                print("Translated Text part:\n\n " + translated_text_part)
            except:
                translated_text_part = "An error occured"

            translated_text = translated_text + translated_text_part

    if step < length:
        textpart = text[step:length]
        try:
            translated_text_part = str(gtranslate.translate(textpart, translation_lang))
            print("Translated Text part:\n\n " + translated_text_part)
        except:
            translated_text_part = "An error occured"

        translated_text = translated_text + translated_text_part


    return translated_text
