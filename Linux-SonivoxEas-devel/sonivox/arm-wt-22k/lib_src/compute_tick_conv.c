#include <stdint.h> // For uint64_t
#include <limits.h> // For USHRT_MAX
#ifdef _MSC_VER
#include <intrin.h> // For _umul128 and _addcarry_u64
#if defined(_M_ARM64) //!(defined(_M_AMD64) || defined(_M_X64))
#pragma intrinsic(__umulh)

uint64_t _umul128(uint64_t a, uint64_t b, uint64_t *high) {
    *high = __umulh(a, b);
    return a * b;
}

uint8_t _addcarry_u64(uint64_t carry_in, uint64_t x, uint64_t y, uint64_t *sum) {
    *sum =  x + y + (carry_in !=0 ? 1 : 0);
    return x > UINT32_MAX - y;
}
#endif
#endif

#define MAX_TICK_CONV USHRT_MAX // Use USHRT_MAX for 16-bit unsigned max value

// pSMFData->tickConv = (EAS_U16) (((temp * 1024) / pSMFData->ppqn + 500) / 1000);

uint16_t compute_tick_conv(uint32_t temp, uint32_t ppqn)
{
    // Guard against division by zero
    if (ppqn == 0) {
        return MAX_TICK_CONV;
    }

    uint64_t temp64;
    int overflow = 0;

#ifdef _MSC_VER
    // MSVC-specific overflow-safe multiplication
    uint64_t high;
    temp64 = _umul128(temp, 1024u, &high);
    if (high != 0) {
        overflow = 1;
    }
#else
    // GCC/Clang-specific overflow-safe multiplication
    if (__builtin_mul_overflow(temp, 1024u, &temp64)) {
        overflow = 1;
    }
#endif

    if (!overflow) {
        temp64 /= ppqn;

#ifdef _MSC_VER
        // MSVC-specific overflow-safe addition
        uint8_t carry = _addcarry_u64(0, temp64, 500, &temp64);
        if (carry) {
            overflow = 1;
        }
#else
        // GCC/Clang-specific overflow-safe addition
        if (__builtin_add_overflow(temp64, 500, &temp64)) {
            overflow = 1;
        }
#endif
    }

    if (!overflow) {
        temp64 /= 1000;
        if (temp64 > MAX_TICK_CONV) {
            overflow = 1;
        }
    }

    if (overflow) {
        return MAX_TICK_CONV;
    }
    return (uint16_t) temp64;
}
