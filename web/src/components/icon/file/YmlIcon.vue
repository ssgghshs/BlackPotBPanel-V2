<template>
  <svg
    xmlns="http://www.w3.org/2000/svg"
    :viewBox="'0 0 1024 1024'"
    :style="iconStyle"
    version="1.1"
    p-id="42557"
    xmlns:xlink="http://www.w3.org/1999/xlink"
  >
    <path
      d="M687.104 192H832L400.896 832H256l215.552-320L256 192h144.896L544 404.416 687.104 192z"
      p-id="42558"
      :fill="iconColor"
    ></path>
  </svg>
</template>

<script setup>
import { defineProps, computed } from 'vue'

const props = defineProps({
  size: {
    type: [Number, String],
    default: 20
  },
  iconColor: {
    type: String,
    default: '#FFCB6B'
  },
  spin: {
    type: Boolean,
    default: false
  }
})

const iconStyle = computed(() => ({
  width: typeof props.size === 'number' ? `${props.size}px` : props.size,
  height: typeof props.size === 'number' ? `${props.size}px` : props.size,
  color: props.iconColor,
  animation: props.spin ? 'spin 1s infinite linear' : 'none'
}))
</script>

<style scoped>
@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}
</style>
