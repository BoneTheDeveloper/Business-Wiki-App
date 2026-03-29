<script setup lang="ts">
</script>

<template>
  <main class="min-h-screen bg-gray-50 flex items-center justify-center">
    <div class="text-center">
      <h1 class="text-4xl font-bold text-primary-600 mb-4">DocWiki</h1>
      <p class="text-gray-600 mb-8">RAG-powered Business Document Wiki</p>
      <div class="flex gap-4 justify-center">
        <router-link
          to="/login"
          class="px-6 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition"
        >
          Login
        </router-link>
        <router-link
          to="/register"
          class="px-6 py-2 border border-primary-600 text-primary-600 rounded-lg hover:bg-primary-50 transition"
        >
          Register
        </router-link>
      </div>
    </div>
  </main>
</template>
