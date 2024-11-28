import asyncio

import requests

# replace your vercel domain
base_url = 'http://localhost:3000'


def custom_generate_audio(payload):
    url = f"{base_url}/api/custom_generate"
    response = requests.post(url, json=payload, headers={'Content-Type': 'application/json'})
    return response.json()


def extend_audio(payload):
    url = f"{base_url}/api/extend_audio"
    response = requests.post(url, json=payload, headers={'Content-Type': 'application/json'})
    return response.json()

def generate_audio_by_prompt(payload):
    url = f"{base_url}/api/generate"
    response = requests.post(url, json=payload, headers={'Content-Type': 'application/json'})
    return response.json()


def get_audio_information(audio_ids):
    url = f"{base_url}/api/get?ids={audio_ids}"
    response = requests.get(url)
    return response.json()


def get_quota_information():
    url = f"{base_url}/api/get_limit"
    response = requests.get(url)
    return response.json()

def get_clip(clip_id):
    url = f"{base_url}/api/clip?id={clip_id}"
    response = requests.get(url)
    return response.json()

def generate_whole_song(clip_id):
    payload = {"clip_id": clip_id}
    url = f"{base_url}/api/concat"
    response = requests.post(url, json=payload)
    return response.json()


if __name__ == '__main__':
    prompt = "A popular heavy metal song about a purple Ostrich, Nostr, sung by a deep-voiced male singer, slowly and melodiously. The lyrics depict hope for a better future."


    has_quota = False
    quota_info = get_quota_information()
    if int(quota_info['credits_left']) >= 20:
         has_quota = True
    else:
        print("No quota left, exiting.")


    if has_quota:

        data = generate_audio_by_prompt({
            "prompt": prompt,
            "make_instrumental": False,
            "wait_audio": False
        })
        if len(data) == 0:
            print("Couldn't create song")
            pass

        ids = f"{data[0]['id']},{data[1]['id']}"
        print(f"ids: {ids}")

        for _ in range(60):
            data = get_audio_information(ids)
            if data[0]["status"] == 'streaming':
                print(f"{data[0]['id']} ==> {data[0]['video_url']}")
                print(f"{data[1]['id']} ==> {data[1]['video_url']}")
                break
            # sleep 5s
            asyncio.sleep(1.0)

        response1 = get_clip(data[0]['id'])
        print(response1['video_url'])
        print(response1['prompt'])

        response2 = get_clip(data[1]['id'])
        print(response2['video_url'])
        print(response2['prompt'])




