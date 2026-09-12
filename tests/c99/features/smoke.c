#include <assert.h>
#include <stdint.h>

uint32_t codin_test_pair_sum(uint8_t a, uint32_t b);
uint32_t codin_test_array_sum(void);
uint32_t codin_test_enum_value(void);
uint32_t codin_test_slice_string(void);
uint32_t codin_test_multiple_returns(void);
uint32_t codin_test_defer(void);
uint32_t codin_test_unions(void);
uint32_t codin_test_imports(void);

int main(void) {
	assert(codin_test_pair_sum(3, 4) == 7);
	assert(codin_test_array_sum() == 10);
	assert(codin_test_enum_value() == 9);
	assert(codin_test_slice_string() == 110);
	assert(codin_test_multiple_returns() == 43);
	assert(codin_test_defer() == 19);
	assert(codin_test_unions() == 49);
	assert(codin_test_imports() == 73);
	return 0;
}
