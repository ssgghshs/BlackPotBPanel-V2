<template>
  <svg
    xmlns="http://www.w3.org/2000/svg"
    :viewBox="'0 0 1024 1024'"
    :style="iconStyle"
    version="1.1"
    p-id="26344"
    xmlns:xlink="http://www.w3.org/1999/xlink"
  >
    <path
      d="M88.064 27.648l77.824 871.424L512 996.352l346.112-97.28 77.824-871.424z"
      p-id="26345"
      :fill="blueColor"
    ></path>
    <path
      d="M771.072 312.32l-10.24 109.568-29.696 328.704L512 811.008l-220.16-60.416-14.336-172.032h107.52l7.168 89.088L512 700.416l119.808-32.768 16.384-148.48-375.808 1.024-11.264-101.376 395.264-4.096 8.192-108.544-413.696 1.024-7.168-101.376h536.576z"
      p-id="26346"
      :fill="whiteColor"
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
  blueColor: {
    type: String,
    default: '#2196F3'
  },
  whiteColor: {
    type: String,
    default: '#FAFAFA'
  },
  spin: {
    type: Boolean,
    default: false
  }
})

const iconStyle = computed(() => ({
  width: typeof props.size === 'number' ? `${props.size}px` : props.size,
  height: typeof props.size === 'number' ? `${props.size}px` : props.size,
  color: props.blueColor,
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
