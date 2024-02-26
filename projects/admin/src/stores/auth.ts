import { defineStore } from 'pinia'
import router from '@/router'
import config from '@/config'
import axios from 'axios'
import qs from 'qs'

export const useAuthStore = defineStore({
  id: 'auth',
  state: () => ({
    // initialize state from local storage to enable user to stay logged in
    user: JSON.parse(localStorage.getItem('user') || 'null'),
    returnUrl: null
  }),
  actions: {
    async login(username: string, password: string) {
      const user = await axios.post(`${config.VISION_AI_API_URL}/auth/token`, qs.stringify({
        username,
        password
      }), {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded'
        }
      }).then(response => {
        // login successful if there's a jwt token in the response
        if (response.data && response.data.access_token) {
          // store user details and jwt token in local storage to keep user logged in between page refreshes
          localStorage.setItem('user', JSON.stringify(response.data))
          return response.data
        }
      })
      // const user = await fetchWrapper.post(`${config.VISION_AI_API_URL}/auth/token`, {
      //   username,
      //   password
      // })

      // update pinia state
      this.user = user

      // store user details and jwt in local storage to keep user logged in between page refreshes
      localStorage.setItem('user', JSON.stringify(user))

      // redirect to previous url or default to home page
      router.push(this.returnUrl || '/')
    },
    logout() {
      this.user = null
      localStorage.removeItem('user')
      router.push('/login')
    }
  }
})
