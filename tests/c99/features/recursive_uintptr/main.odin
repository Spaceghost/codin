package recursive_uintptr

decimal_size :: proc "contextless" (value: uintptr) -> uintptr {
	if value < 10 {
		return 1
	}
	return 1 + decimal_size(value / 10)
}

@(export)
codin_test_recursive_uintptr :: proc "c" () -> uintptr {
	return decimal_size(12345)
}
