package imports

import helper "./helper"

@(export)
codin_test_imports :: proc "c" () -> u32 {
	return helper.answer()
}
