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
      if (import.meta.env.DEV) console.log('🔄 Users Store: Starting fetchUsers...')
      this.loading = true
      this.error = null
      
      try {
        const response = await adminAPI.getUsers()
        
        if (Array.isArray(response)) {
          this.users = response
          if (import.meta.env.DEV) console.log(`✅ Users Store: Stored ${response.length} users`)
        } else {
          console.error('❌ Users Store: Response is not an array:', typeof response)
          throw new Error('Invalid response format - expected array')
        }
        
        this.lastUpdated = new Date()
        
      } catch (error) {
        console.error('❌ Users Store: Error fetching users:', error)
        if (import.meta.env.DEV) {
          console.error('❌ Error details:', error.response?.data)
        }
        
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
      }
    },

    async createUser(userData) {
      if (import.meta.env.DEV) console.log('🔄 Users Store: Creating user:', userData.username)
      this.loading = true
      this.error = null
      
      try {
        const response = await adminAPI.createUser(userData)
        if (import.meta.env.DEV) console.log('✅ Users Store: User created successfully')
        
        // Add the new user to the store instead of refetching the entire list
        if (response.user) {
          this.users.push(response.user)
          this.lastUpdated = new Date()
          if (import.meta.env.DEV) console.log('✅ Users Store: Added new user to store')
        } else {
          // Fallback to refetching if user data isn't returned for some reason
          if (import.meta.env.DEV) console.log('⚠️ Users Store: No user data returned, refetching list')
          await this.fetchUsers()
        }
        
        return response
      } catch (error) {
        console.error('❌ Users Store: Error creating user:', error.message)
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
      if (import.meta.env.DEV) console.log('🔄 Users Store: Deactivating user:', userId)
      this.loading = true
      this.error = null
      
      try {
        const response = await adminAPI.deactivateUser(userId)
        if (import.meta.env.DEV) console.log('✅ Users Store: User deactivated successfully')
        
        // Update user in store immediately for better UX
        const userIndex = this.users.findIndex(user => user.id === userId)
        if (userIndex !== -1) {
          this.users[userIndex].is_active = false
        }
        
        return response
      } catch (error) {
        console.error('❌ Users Store: Error deactivating user:', error.message)
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
      if (import.meta.env.DEV) console.log('🔄 Users Store: Permanently deleting user:', userId)
      this.loading = true
      this.error = null
      
      try {
        const response = await adminAPI.deleteUser(userId)
        if (import.meta.env.DEV) console.log('✅ Users Store: User permanently deleted')
        
        // Remove user from store immediately
        const userIndex = this.users.findIndex(user => user.id === userId)
        if (userIndex !== -1) {
          const deletedUser = this.users[userIndex]
          this.users.splice(userIndex, 1)
        }
        
        return response
      } catch (error) {
        console.error('❌ Users Store: Error deleting user:', error.message)
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

    async bulkDeleteUsers(userIds) {
      if (import.meta.env.DEV) console.log('🔄 Users Store: Bulk deleting users:', userIds)
      this.loading = true
      this.error = null
      
      try {
        const response = await adminAPI.bulkDeleteUsers(userIds)
        if (import.meta.env.DEV) console.log('✅ Users Store: Bulk delete completed')
        
        // Remove successfully deleted users from store
        if (response.deleted_users) {
          // Remove by username since that's what we get back
          const deletedUsernames = response.deleted_users
          this.users = this.users.filter(user => !deletedUsernames.includes(user.username))
        } else if (response.successful_deletions > 0) {
          // Fallback: remove by user ID if we don't get usernames back
          this.users = this.users.filter(user => !userIds.includes(user.id))
        }
        
        return response
      } catch (error) {
        console.error('❌ Users Store: Error in bulk delete:', error.message)
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
      if (import.meta.env.DEV) console.log('🧹 Users Store: Clearing error')
      this.error = null
    },

    reset() {
      if (import.meta.env.DEV) console.log('🔄 Users Store: Resetting store')
      this.users = []
      this.loading = false
      this.error = null
      this.lastUpdated = null
    },

    // For debugging
    logState() {
      if (import.meta.env.DEV) {
        console.log('📊 Users Store State:')
        console.log('  Users:', this.users.length)
        console.log('  Loading:', this.loading)
        console.log('  Error:', this.error)
        console.log('  Last Updated:', this.lastUpdated)
        console.log('  Active Users:', this.activeUserCount, '/', this.userCount)
      }
    }
  }
})