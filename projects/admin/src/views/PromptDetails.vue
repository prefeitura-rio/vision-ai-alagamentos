<template>
  <div>
    <h2>Prompt Details</h2>
    <div class="mb-3">
      <label for="id" class="form-label">ID</label>
      <input type="text" id="id" v-model="prompt.id" class="form-control" disabled />
    </div>
    <div class="mb-3">
      <label for="name" class="form-label">Name</label>
      <input type="text" id="name" v-model="prompt.name" class="form-control" @input="enableSave" />
    </div>
    <div class="mb-3">
      <label for="model" class="form-label">Model</label>
      <input
        type="text"
        id="model"
        v-model="prompt.model"
        class="form-control"
        @input="enableSave"
      />
    </div>
    <div class="mb-3">
      <label for="prompt-text" class="form-label">Prompt Text</label>
      <textarea
        id="prompt-text"
        v-model="prompt.prompt_text"
        class="form-control"
        rows="4"
        @input="enableSave"
      ></textarea>
    </div>
    <div class="mb-3">
      <label for="max-output-token" class="form-label">Max Output Token</label>
      <input
        type="number"
        id="max-output-token"
        v-model="prompt.max_output_token"
        class="form-control"
        @input="enableSave"
      />
    </div>
    <div class="mb-3">
      <label for="temperature" class="form-label">Temperature</label>
      <input
        type="number"
        id="temperature"
        v-model="prompt.temperature"
        class="form-control"
        step="0.1"
        @input="enableSave"
      />
    </div>
    <div class="mb-3">
      <label for="top-k" class="form-label">Top K</label>
      <input
        type="number"
        id="top-k"
        v-model="prompt.top_k"
        class="form-control"
        @input="enableSave"
      />
    </div>
    <div class="mb-3">
      <label for="top-p" class="form-label">Top P</label>
      <input
        type="number"
        id="top-p"
        v-model="prompt.top_p"
        class="form-control"
        step="0.1"
        @input="enableSave"
      />
    </div>
    <button :disabled="!isFormModified" @click="saveChanges" class="btn btn-primary">Save</button>
    <!-- add some horizontal spacing between buttons -->
    <span class="mx-2"></span>
    <button @click="deletePrompt" class="btn btn-danger">Delete</button>

    <div class="my-4"></div>

    <h3>Associated Objects</h3>
    <div class="mb-3">
      <label for="objectId" class="form-label">Object ID</label>
      <input type="text" id="objectId" v-model="newObjectId" class="form-control" />
    </div>
    <button @click="addObject" class="btn btn-primary">Add Object</button>
    <div class="my-4"></div>
    <table class="table">
      <thead>
        <tr>
          <th>ID</th>
          <th>Name</th>
          <th>Delete</th>
        </tr>
      </thead>
      <tbody ref="sortableObjects">
        <tr v-for="object in associatedObjects" :key="object.id" :data-object-id="object.slug">
          <td>{{ object.id }}</td>
          <td>{{ object.name }}</td>
          <td>
            <button class="btn btn-danger" @click="removeObject(object.id)">Delete</button>
          </td>
        </tr>
      </tbody>
    </table>
    <button @click="reorderObjects" class="btn btn-primary">Save Order</button>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { apiRequest } from '../_helpers/api-request'
import Sortable from 'sortablejs'

const router = useRouter()
const promptId = router.currentRoute.value.params.id
const prompt = ref({})
const associatedObjects = ref([])
const newObjectId = ref('')
const isFormModified = ref(false)
const isOrderModified = ref(false)
const sortableObjects = ref(null)

const getPromptDetails = async () => {
  try {
    const response = await apiRequest.get(`/prompts/${promptId}`)
    prompt.value = response
    await getAssociatedObjects()
  } catch (error) {
    console.error('Error fetching prompt details:', error)
  }
}

const enableSave = () => {
  isFormModified.value = true
}

const saveChanges = async () => {
  try {
    await apiRequest.put(`/prompts/${promptId}`, prompt.value)
    isFormModified.value = false
    alert('Changes saved successfully!')
  } catch (error) {
    console.error('Error saving changes:', error)
  }
}

const deletePrompt = async () => {
  try {
    if (confirm('Are you sure you want to delete this prompt?')) {
      await apiRequest.delete(`/prompts/${promptId}`)
      router.push('/prompts')
    }
  } catch (error) {
    console.error('Error deleting prompt:', error)
  }
}

const getAssociatedObjects = async () => {
  try {
    const response = await apiRequest.get(`/prompts/${promptId}/objects`)
    associatedObjects.value = response
  } catch (error) {
    console.error('Error fetching associated objects:', error)
  }
}

const addObject = async () => {
  try {
    await apiRequest.post(`/prompts/${promptId}/objects?object_id=${newObjectId.value}`)
    await getAssociatedObjects()
    newObjectId.value = ''
  } catch (error) {
    console.error('Error adding object:', error)
  }
}

const removeObject = async (objectId: string) => {
  try {
    if (confirm('Are you sure you want to remove this object from the prompt?')) {
      await apiRequest.delete(`/prompts/${promptId}/objects/${objectId}`)
      await getAssociatedObjects()
    }
  } catch (error) {
    console.error('Error removing object:', error)
  }
}

const reorderObjects = async () => {
  if (confirm('Are you sure you want to reorder the objects?')) {
    try {
      const objectsOrder = Array.from(sortableObjects.value.children).map(
        (tr: any) => tr.dataset.objectId
      )
      const requestBody = { objects: objectsOrder }
      await apiRequest.post(`/prompts/${promptId}/objects/order`, requestBody)
      alert('Objects reordered successfully!')
    } catch (error) {
      console.error('Error reordering objects:', error)
      alert('Failed to reorder objects. Please try again.')
    }
  }
}

onMounted(() => {
  getPromptDetails()
  if (sortableObjects.value) {
    const sortable = new Sortable(sortableObjects.value, {
      onEnd: () => {
        isOrderModified.value = true
      }
    })
  } else {
    console.error('Sortable objects container not found')
  }
})
</script>
