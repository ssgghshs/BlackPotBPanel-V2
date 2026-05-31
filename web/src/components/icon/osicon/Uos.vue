<template>
  <svg
    xmlns="http://www.w3.org/2000/svg"
    :viewBox="'0 0 1024 1024'"
    :style="iconStyle"
    version="1.1"
    p-id="7368"
    xmlns:xlink="http://www.w3.org/1999/xlink"
  >
    <path
      d="M512 1024A512 512 0 1 0 512 0a512 512 0 0 0 0 1024z"
      fill="#01B4FE"
      p-id="7369"
    ></path>
    <path
      d="M512 800c-42.688 0-83.2-8.96-121.792-27.008a224.384 224.384 0 0 1-97.792-84.608C268.16 650.56 256 605.824 256 554.24V330.24c0-11.392 3.84-21.312 11.52-29.696A39.872 39.872 0 0 1 296.96 288c11.264 0 21.056 4.224 29.312 12.608 8.32 8.384 12.48 18.304 12.48 29.696v226.624c0 36.608 8.32 66.944 24.896 90.88 15.36 24.64 36.096 43.52 62.208 56.768 26.624 12.608 55.424 18.88 86.208 18.88a197.12 197.12 0 0 0 85.312-18.88 148.8 148.8 0 0 0 64.896-57.6c15.424-25.856 23.104-55.872 23.104-90.048v-226.56c0-11.456 3.84-21.376 11.52-29.76a39.872 39.872 0 0 1 29.44-12.608c11.2 0 20.992 4.224 29.312 12.608A40.96 40.96 0 0 1 768 330.24V554.24c0 52.8-12.416 98.112-37.312 135.936-24.32 36.032-56 63.36-95.104 81.92A280.384 280.384 0 0 1 512 800z"
      fill="#FFFFFF"
      p-id="7370"
    ></path>
  </svg>
</template>

<script setup>
import { defineProps, computed } from 'vue'

const props = defineProps({
  size: {
    type: [Number, String],
    default: 16
  },
  color: {
    type: String,
    default: 'currentColor'
  },
  spin: {
    type: Boolean,
    default: false
  }
})

const iconStyle = computed(() => ({
  width: typeof props.size === 'number' ? `${props.size}px` : props.size,
  height: typeof props.size === 'number' ? `${props.size}px` : props.size,
  color: props.color,
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
