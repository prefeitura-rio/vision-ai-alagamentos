<template>
  <div>
    <h2>Create New Prompt</h2>
    <div class="mb-3">
      <label for="name" class="form-label">Name</label>
      <input type="text" id="name" v-model="newPrompt.name" class="form-control" />
    </div>
    <div class="mb-3">
      <label for="model" class="form-label">Model</label>
      <input type="text" id="model" v-model="newPrompt.model" class="form-control" />
    </div>
    <div class="mb-3">
      <label for="promptText" class="form-label">Prompt Text</label>
      <textarea
        id="promptText"
        v-model="newPrompt.prompt_text"
        class="form-control"
        rows="6"
      ></textarea>
    </div>
    <div class="mb-3">
      <label for="maxOutputToken" class="form-label">Max Output Token</label>
      <input
        type="number"
        id="maxOutputToken"
        v-model="newPrompt.max_output_token"
        class="form-control"
      />
    </div>
    <div class="mb-3">
      <label for="temperature" class="form-label">Temperature</label>
      <input type="number" id="temperature" v-model="newPrompt.temperature" class="form-control" />
    </div>
    <div class="mb-3">
      <label for="topK" class="form-label">Top K</label>
      <input type="number" id="topK" v-model="newPrompt.top_k" class="form-control" />
    </div>
    <div class="mb-3">
      <label for="topP" class="form-label">Top P</label>
      <input type="number" id="topP" v-model="newPrompt.top_p" class="form-control" />
    </div>
    <button @click="createPrompt" class="btn btn-primary">Create</button>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { apiRequest } from '../_helpers/api-request'

const router = useRouter()
const newPrompt = ref({
  name: '',
  model: '',
  prompt_text: '',
  max_output_token: 0,
  temperature: 0,
  top_k: 0,
  top_p: 0
})

const createPrompt = async () => {
  try {
    await apiRequest.post('/prompts', newPrompt.value)
    router.push('/prompts')
  } catch (error) {
    console.error('Error creating prompt:', error)
  }
}
</script>
