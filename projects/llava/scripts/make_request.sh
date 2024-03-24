if [ "$#" -ne 2 ]; then
  echo "Usage: $0 <model_family> <image_bucket_path>"
  exit 1
fi


model_family=$1
if [[ $model_family == "mistral" ]]; then
  curl http://localhost:40000/ -X POST -L -H "Content-Type: application/json" --data '{"prompt":"[INST] <image>\nWhat is shown in this image? [/INST]", "images": ["https://storage.googleapis.com/'$2'"]}'
elif [[ $model_family == "vicuna" ]]; then
  curl http://localhost:40000/ -X POST -L -H "Content-Type: application/json" --data '{"prompt":"A chat between a curious human and an artificial intelligence assistant. The assistant gives helpful, detailed, and polite answers to the humans questions. USER: <image>\nWhat is shown in this image? ASSISTANT:", "images": ["https://storage.googleapis.com/'$2'"]}'
elif [[ $model_family == "hermes-yi" ]]; then
  curl http://localhost:40000/ -X POST -L -H "Content-Type: application/json" --data '{"prompt":"<|im_start|>system\\nAnswer the questions.<|im_end|><|im_start|>user\\n<image>\\nWhat is shown in this image?<|im_end|><|im_start|>assistant\\n", "images": ["https://storage.googleapis.com/'$2'"]}'
else
  echo "Invalid model family: $model_family"
fi
