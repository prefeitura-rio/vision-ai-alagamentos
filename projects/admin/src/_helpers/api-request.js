import axios from 'axios'
import { useAuthStore } from '../stores/auth'
import config from '../config'

export const apiRequest = {
    get: request('GET'),
    post: request('POST'),
    put: request('PUT'),
    delete: request('DELETE'),
}

function request(method) {
    return async (path, data) => {
        const url = `${config.VISION_AI_API_URL}${path}`
        const headers = authHeader(url)
        const response = await axios({ method, url, data, headers })
        if (response.status == 200) {
            return response.data
        }
        throw new Error(response.statusText)
    }
}

function authHeader() {
    const { user } = useAuthStore();
    const isLoggedIn = !!user?.access_token;
    if (isLoggedIn) {
        return { Authorization: `Bearer ${user.access_token}` };
    } else {
        throw new Error('Not logged in');
    }
}