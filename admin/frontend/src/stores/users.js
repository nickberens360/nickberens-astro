import { defineStore } from 'pinia'
import { adminAPI } from '../services/api.js'

export const useUsersStore = defineStore('users', {
  state: () => ({
    users: [],
    loading: false,
    error: null,
    lastUpdated: null
  }),

  getters: {
    activeUsers: (state) => state.users.filter(user => user.is_active),
    inactiveUsers: (state) => state.users.filter(user => !user.is_active),
    userCount: (state) => state.users.length,
    activeUserCount: (state) => state.users.filter(user => user.is_active).length,
    adminUsers: (state) => state.users.filter(user => user.role === 'admin'),
    viewerUsers: (state) => state.users.filter(user => user.role === 'viewer'),
    
    getUserById: (state) => (id) => state.users.find(user => user.id === id),
    getUserByUsername: (state) => (username) => state.users.find(user => user.username === username),
  },

  actions: {
    async fetchUsers() {
      console.log('🔄 Users Store: Starting fetchUsers...')
      this.loading = true
      this.error = null
      
      try {
        console.log('🔄 Users Store: Making API call to getUsers...')
        const response = await adminAPI.getUsers()
        console.log('✅ Users Store: API response received:', response)
        
        if (Array.isArray(response)) {
          this.users = response
          console.log(`✅ Users Store: Stored ${response.length} users:`, this.users)
        } else {
          console.error('❌ Users Store: Response is not an array:', typeof response, response)
          throw new Error('Invalid response format - expected array')
        }
        
        this.lastUpdated = new Date()
        console.log('✅ Users Store: Users loaded successfully at', this.lastUpdated)
        
      } catch (error) {
        console.error('❌ Users Store: Error fetching users:', error)
        console.error('❌ Users Store: Error response:', error.response?.data)
        console.error('❌ Users Store: Error status:', error.response?.status)
        console.error('❌ Users Store: Error headers:', error.response?.headers)
        
        this.error = {
          message: error.message,
          status: error.response?.status,
          data: error.response?.data,
          timestamp: new Date()
        }
        
        // Don't clear users on error - keep previous data if available
        if (!this.users.length) {
          this.users = []
        }
        
        throw error
      } finally {
        this.loading = false
        console.log('🏁 Users Store: fetchUsers completed. Loading:', this.loading)
      }
    },

    async createUser(userData) {
      console.log('🔄 Users Store: Creating user:', userData)
      this.loading = true
      this.error = null
      
      try {
        const response = await adminAPI.createUser(userData)
        console.log('✅ Users Store: User created:', response)
        
        // Refresh users list to include the new user
        await this.fetchUsers()
        
        return response
      } catch (error) {
        console.error('❌ Users Store: Error creating user:', error)
        this.error = {
          message: error.message,
          status: error.response?.status,
          data: error.response?.data,
          timestamp: new Date()
        }
        throw error
      } finally {
        this.loading = false
      }
    },

    async deactivateUser(userId) {
      console.log('🔄 Users Store: Deactivating user:', userId)
      this.loading = true
      this.error = null
      
      try {
        const response = await adminAPI.deactivateUser(userId)
        console.log('✅ Users Store: User deactivated:', response)
        
        // Update user in store immediately for better UX
        const userIndex = this.users.findIndex(user => user.id === userId)
        if (userIndex !== -1) {
          this.users[userIndex].is_active = false
          console.log('✅ Users Store: Updated user in store:', this.users[userIndex])
        }
        
        return response
      } catch (error) {
        console.error('❌ Users Store: Error deactivating user:', error)
        this.error = {
          message: error.message,
          status: error.response?.status,
          data: error.response?.data,
          timestamp: new Date()
        }
        throw error
      } finally {
        this.loading = false
      }
    },

    async deleteUser(userId) {
      console.log('🔄 Users Store: Permanently deleting user:', userId)
      this.loading = true
      this.error = null
      
      try {
        const response = await adminAPI.deleteUser(userId)
        console.log('✅ Users Store: User permanently deleted:', response)
        
        // Remove user from store immediately
        const userIndex = this.users.findIndex(user => user.id === userId)
        if (userIndex !== -1) {
          const deletedUser = this.users[userIndex]
          this.users.splice(userIndex, 1)
          console.log('✅ Users Store: Removed user from store:', deletedUser.username)
        }
        
        return response
      } catch (error) {
        console.error('❌ Users Store: Error deleting user:', error)
        this.error = {
          message: error.message,
          status: error.response?.status,
          data: error.response?.data,
          timestamp: new Date()
        }
        throw error
      } finally {
        this.loading = false
      }
    },

    // Utility actions
    clearError() {
      console.log('🧹 Users Store: Clearing error')
      this.error = null
    },

    reset() {
      console.log('🔄 Users Store: Resetting store')
      this.users = []
      this.loading = false
      this.error = null
      this.lastUpdated = null
    },

    // For debugging
    logState() {
      console.log('📊 Users Store State:')
      console.log('  Users:', this.users)
      console.log('  Loading:', this.loading)
      console.log('  Error:', this.error)
      console.log('  Last Updated:', this.lastUpdated)
      console.log('  Active Users:', this.activeUserCount, '/', this.userCount)
    }
  }
})