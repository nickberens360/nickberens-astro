<template>
  <div class="queries-view">
    <h1 class="text-h4 font-weight-bold mb-6">Query Explorer</h1>
    
    <QueryTable
      title="All Queries"
      @query-selected="handleQuerySelected"
    />
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useQueriesStore } from '@/stores/queries'
import QueryTable from '@/components/QueryTable.vue'

const queriesStore = useQueriesStore()

const handleQuerySelected = (query) => {
  console.log('Selected query:', query)
}

onMounted(async () => {
  await queriesStore.fetchQueries()
})
</script>

<style scoped>
.queries-view {
  max-width: 1400px;
  margin: 0 auto;
}
</style>