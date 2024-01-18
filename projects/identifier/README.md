

Test request example:

```json
{
  "data": {
      "image_base64": "image_base64",
      "prompt":"You are an expert flooding detector. You are given a image. You must detect if there is flooding in the image. The output MUST be a JSON object with a boolean value for the key 'label'. If you don't know what to anwser, you can set the key 'label' as false. Example: {'label': true}",
      "google_api_model":"gemini-pro-vision",
      "max_output_tokens": 256,
      "temperature": 0.4,
      "top_k": 32,
      "top_p": 1
  },
  "type": "google.cloud.pubsub.topic.v1.messagePublished",
  "specversion": "1.0",
  "source": "//pubsub.googleapis.com/",
  "id": "1234567890"
}
```