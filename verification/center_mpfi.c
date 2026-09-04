/*
 * Copyright 2026 Ruturaj R Raval
 * SPDX-License-Identifier: Apache-2.0
 *
 * Independent MPFI verifier for the canonical minimum-overlap center
 * certificate. All certificate decimals and subdivision endpoints are kept
 * as exact GMP rationals. MPFI supplies directed interval enclosures for the
 * transcendental evaluations and all subsequent arithmetic.
 */

#include <errno.h>
#include <limits.h>
#include <stdbool.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <gmp.h>
#include <mpfi.h>
#include <mpfr.h>

#define CERTIFICATE_SCHEMA "minimum-overlap-center-certificate-v1"
#define MAX_CERTIFICATE_BYTES (1024UL * 1024UL)
#define MAX_DECIMAL_BYTES 128UL
#define MAX_COSINE_ROWS 512UL
#define MAX_PARSEVAL_ORDER 1000UL
#define MAX_FREQUENCY 10000UL
#define MIN_PRECISION_BITS 128UL
#define MAX_PRECISION_BITS 4096UL
#define MAX_INITIAL_CELLS 65536UL
#define MAX_BISECTION_DEPTH 30UL
#define MAX_VISITED_CELLS 10000000ULL
#define OUTPUT_DIGITS 40UL

typedef struct {
    char text[256];
} Failure;

typedef struct {
    mpq_t frequency;
    mpq_t multiplier;
} CosineRow;

typedef struct {
    mpq_t target;
    mpq_t mean_abs_max;
    mpq_t second_moment_multiplier;
    mpq_t parseval_multiplier;
    unsigned long parseval_order;
    size_t cosine_count;
    CosineRow *cosines;
    char target_text[MAX_DECIMAL_BYTES + 1UL];
} Certificate;

typedef struct {
    mpfi_t frequency;
    mpfi_t coefficient;
    mpfi_t derivative_coefficient;
    mpfi_t second_derivative_coefficient;
    mpfi_t primitive_coefficient;
} Term;

typedef struct {
    mpfr_prec_t precision;
    mpfi_t constant;
    mpfi_t quadratic;
    mpfi_t third_derivative_bound;
    size_t term_count;
    size_t initialized_terms;
    Term *terms;
} CompiledCertificate;

typedef struct {
    mpfi_t x;
    mpfi_t x_squared;
    mpfi_t value;
    mpfi_t derivative;
    mpfi_t second_derivative;
    mpfi_t argument;
    mpfi_t sine;
    mpfi_t cosine;
    mpfi_t temporary;
    mpfi_t temporary_two;
    mpfi_t radius;
    mpfi_t error;
    mpfi_t absolute;
    mpfi_t symmetric_error;
    mpfi_t x_cubed;
    mpfr_t lower;
    mpfr_t upper;
} Workspace;

typedef struct {
    uint64_t visited_cells;
    uint64_t negative_cells;
    uint64_t positive_cells;
    uint64_t split_cells;
    uint64_t terminal_cells;
    unsigned long max_depth_seen;
    bool pending_positive;
    mpq_t pending_left;
    mpq_t pending_right;
    mpfi_t positive_integral;
    mpfi_t uncertain_integral;
} Audit;

typedef struct {
    const CompiledCertificate *certificate;
    Failure *failure;
    unsigned long max_depth;
    Workspace workspace;
    Audit audit;
    mpfi_t range;
    mpfi_t antiderivative_left;
    mpfi_t antiderivative_right;
    mpfi_t contribution;
    mpfi_t charge;
} Verification;

static bool fail(Failure *failure, const char *format, ...)
{
    va_list arguments;

    if (failure->text[0] != '\0') {
        return false;
    }
    va_start(arguments, format);
    (void)vsnprintf(failure->text, sizeof(failure->text), format, arguments);
    va_end(arguments);
    return false;
}

static bool interval_is_finite(mpfi_srcptr value)
{
    return mpfi_bounded_p(value) != 0 && mpfi_nan_p(value) == 0
        && mpfi_inf_p(value) == 0;
}

static void certificate_init(Certificate *certificate)
{
    memset(certificate, 0, sizeof(*certificate));
    mpq_init(certificate->target);
    mpq_init(certificate->mean_abs_max);
    mpq_init(certificate->second_moment_multiplier);
    mpq_init(certificate->parseval_multiplier);
}

static void certificate_clear(Certificate *certificate)
{
    size_t index;

    for (index = 0; index < certificate->cosine_count; ++index) {
        mpq_clear(certificate->cosines[index].frequency);
        mpq_clear(certificate->cosines[index].multiplier);
    }
    free(certificate->cosines);
    mpq_clear(certificate->target);
    mpq_clear(certificate->mean_abs_max);
    mpq_clear(certificate->second_moment_multiplier);
    mpq_clear(certificate->parseval_multiplier);
}

static bool read_certificate_payload(
    const char *path,
    char **payload_out,
    size_t *length_out,
    Failure *failure
)
{
    FILE *stream;
    char *payload;
    size_t used;

    stream = fopen(path, "rb");
    if (stream == NULL) {
        return fail(failure, "cannot_open_certificate:%s", strerror(errno));
    }
    payload = malloc(MAX_CERTIFICATE_BYTES + 2UL);
    if (payload == NULL) {
        (void)fclose(stream);
        return fail(failure, "allocation_failure");
    }

    used = 0;
    while (used < MAX_CERTIFICATE_BYTES + 1UL) {
        size_t count = fread(
            payload + used,
            1,
            MAX_CERTIFICATE_BYTES + 1UL - used,
            stream
        );
        used += count;
        if (ferror(stream) != 0) {
            free(payload);
            (void)fclose(stream);
            return fail(failure, "certificate_read_failure");
        }
        if (feof(stream) != 0) {
            break;
        }
        if (count == 0) {
            free(payload);
            (void)fclose(stream);
            return fail(failure, "certificate_read_stalled");
        }
    }
    if (used > MAX_CERTIFICATE_BYTES) {
        free(payload);
        (void)fclose(stream);
        return fail(failure, "certificate_too_large");
    }
    if (fclose(stream) != 0) {
        free(payload);
        return fail(failure, "certificate_close_failure");
    }

    payload[used] = '\0';
    *payload_out = payload;
    *length_out = used;
    return true;
}

static bool validate_payload_bytes(
    const char *payload,
    size_t length,
    Failure *failure
)
{
    size_t index;

    if (length == 0 || payload[length - 1UL] != '\n') {
        return fail(failure, "certificate_must_end_with_lf");
    }
    for (index = 0; index < length; ++index) {
        unsigned char byte = (unsigned char)payload[index];

        if (byte == '\r' || byte == '\0' || byte > 0x7eU) {
            return fail(failure, "certificate_must_be_lf_ascii");
        }
        if (byte < 0x20U && byte != '\n' && byte != '\t') {
            return fail(failure, "certificate_contains_control_byte");
        }
    }
    return true;
}

static bool split_lines(
    char *payload,
    size_t length,
    char ***lines_out,
    size_t *line_count_out,
    Failure *failure
)
{
    char **lines;
    size_t line_count;
    size_t line_index;
    size_t start;
    size_t index;

    line_count = 0;
    for (index = 0; index < length; ++index) {
        if (payload[index] == '\n') {
            ++line_count;
        }
    }
    if (line_count < 8UL) {
        return fail(failure, "certificate_is_incomplete");
    }
    lines = calloc(line_count, sizeof(*lines));
    if (lines == NULL) {
        return fail(failure, "allocation_failure");
    }

    line_index = 0;
    start = 0;
    for (index = 0; index < length; ++index) {
        if (payload[index] != '\n') {
            continue;
        }
        if (index == start) {
            free(lines);
            return fail(failure, "certificate_contains_empty_line");
        }
        payload[index] = '\0';
        lines[line_index++] = payload + start;
        start = index + 1UL;
    }
    if (line_index != line_count || start != length) {
        free(lines);
        return fail(failure, "certificate_line_split_failure");
    }

    *lines_out = lines;
    *line_count_out = line_count;
    return true;
}

static bool canonical_decimal_to_mpq(
    const char *token,
    mpq_t output,
    const char *field_name,
    Failure *failure
)
{
    size_t length;
    size_t index;
    size_t dot_index;
    size_t fractional_digits;
    mpz_t numerator;
    mpz_t denominator;

    length = strlen(token);
    if (length == 0 || length > MAX_DECIMAL_BYTES) {
        return fail(failure, "invalid_decimal:%s", field_name);
    }
    if (token[0] == '0' && length > 1UL && token[1] != '.') {
        return fail(failure, "invalid_decimal:%s", field_name);
    }
    if (token[0] < '0' || token[0] > '9') {
        return fail(failure, "invalid_decimal:%s", field_name);
    }

    dot_index = length;
    for (index = 0; index < length; ++index) {
        char character = token[index];

        if (character == '.') {
            if (dot_index != length || index == 0) {
                return fail(failure, "invalid_decimal:%s", field_name);
            }
            dot_index = index;
        } else if (character < '0' || character > '9') {
            return fail(failure, "invalid_decimal:%s", field_name);
        }
    }
    if (dot_index < length) {
        if (dot_index + 1UL == length || token[length - 1UL] == '0') {
            return fail(failure, "invalid_decimal:%s", field_name);
        }
        fractional_digits = length - dot_index - 1UL;
    } else {
        fractional_digits = 0;
    }

    mpz_init_set_ui(numerator, 0);
    mpz_init_set_ui(denominator, 1);
    for (index = 0; index < length; ++index) {
        if (token[index] == '.') {
            continue;
        }
        mpz_mul_ui(numerator, numerator, 10);
        mpz_add_ui(numerator, numerator, (unsigned long)(token[index] - '0'));
    }
    if (fractional_digits > 0) {
        mpz_ui_pow_ui(denominator, 10, fractional_digits);
    }
    mpq_set_num(output, numerator);
    mpq_set_den(output, denominator);
    mpq_canonicalize(output);
    mpz_clear(numerator);
    mpz_clear(denominator);
    return true;
}

static bool canonical_unsigned_long(
    const char *token,
    unsigned long *output,
    const char *field_name,
    Failure *failure
)
{
    unsigned long value;
    size_t length;
    size_t index;

    length = strlen(token);
    if (length == 0 || (token[0] == '0' && length != 1UL)) {
        return fail(failure, "invalid_integer:%s", field_name);
    }
    value = 0;
    for (index = 0; index < length; ++index) {
        unsigned long digit;

        if (token[index] < '0' || token[index] > '9') {
            return fail(failure, "invalid_integer:%s", field_name);
        }
        digit = (unsigned long)(token[index] - '0');
        if (value > (ULONG_MAX - digit) / 10UL) {
            return fail(failure, "integer_overflow:%s", field_name);
        }
        value = value * 10UL + digit;
    }
    *output = value;
    return true;
}

static bool named_field(
    char *line,
    const char *expected_name,
    char **value_out,
    Failure *failure
)
{
    size_t name_length = strlen(expected_name);
    size_t line_length = strlen(line);
    char *value;

    *value_out = NULL;
    if (line_length <= name_length
        || strncmp(line, expected_name, name_length) != 0
        || line[name_length] != '\t') {
        return fail(failure, "expected_field:%s", expected_name);
    }
    value = line + name_length + 1UL;
    if (*value == '\0' || strchr(value, '\t') != NULL) {
        return fail(failure, "malformed_field:%s", expected_name);
    }
    *value_out = value;
    return true;
}

static bool parse_certificate(
    const char *path,
    Certificate *certificate,
    Failure *failure
)
{
    char *payload = NULL;
    char **lines = NULL;
    char *token = NULL;
    size_t length = 0;
    size_t line_count = 0;
    unsigned long declared_cosine_count;
    mpq_t expected_mean;
    size_t index;
    bool result = false;

    if (!read_certificate_payload(path, &payload, &length, failure)
        || !validate_payload_bytes(payload, length, failure)
        || !split_lines(payload, length, &lines, &line_count, failure)) {
        goto cleanup;
    }
    if (lines == NULL || line_count < 8UL) {
        (void)fail(failure, "certificate_line_split_failure");
        goto cleanup;
    }
    if (strcmp(lines[0], CERTIFICATE_SCHEMA) != 0) {
        (void)fail(failure, "unexpected_certificate_schema");
        goto cleanup;
    }

    if (!named_field(lines[1], "target", &token, failure)) {
        goto cleanup;
    }
    if (token == NULL
        || !canonical_decimal_to_mpq(
            token,
            certificate->target,
            "target",
            failure
        )) {
        goto cleanup;
    }
    (void)memcpy(certificate->target_text, token, strlen(token) + 1UL);

    if (!named_field(lines[2], "mean_abs_max", &token, failure)) {
        goto cleanup;
    }
    if (token == NULL
        || !canonical_decimal_to_mpq(
            token,
            certificate->mean_abs_max,
            "mean_abs_max",
            failure
        )) {
        goto cleanup;
    }
    if (!named_field(
        lines[3],
        "second_moment_multiplier",
        &token,
        failure
    )) {
        goto cleanup;
    }
    if (token == NULL
        || !canonical_decimal_to_mpq(
            token,
            certificate->second_moment_multiplier,
            "second_moment_multiplier",
            failure
        )) {
        goto cleanup;
    }
    if (!named_field(lines[4], "parseval_order", &token, failure)) {
        goto cleanup;
    }
    if (token == NULL
        || !canonical_unsigned_long(
            token,
            &certificate->parseval_order,
            "parseval_order",
            failure
        )) {
        goto cleanup;
    }
    if (!named_field(lines[5], "parseval_multiplier", &token, failure)) {
        goto cleanup;
    }
    if (token == NULL
        || !canonical_decimal_to_mpq(
            token,
            certificate->parseval_multiplier,
            "parseval_multiplier",
            failure
        )) {
        goto cleanup;
    }
    if (!named_field(lines[6], "cosine_count", &token, failure)) {
        goto cleanup;
    }
    if (token == NULL
        || !canonical_unsigned_long(
            token,
            &declared_cosine_count,
            "cosine_count",
            failure
        )) {
        goto cleanup;
    }

    if (mpq_sgn(certificate->target) <= 0
        || mpq_cmp_ui(certificate->target, 1, 1) >= 0) {
        (void)fail(failure, "target_out_of_range");
        goto cleanup;
    }
    mpq_init(expected_mean);
    mpq_set_ui(expected_mean, 1, 320);
    if (mpq_cmp(certificate->mean_abs_max, expected_mean) != 0) {
        mpq_clear(expected_mean);
        (void)fail(failure, "mean_abs_max_must_equal_1_over_320");
        goto cleanup;
    }
    mpq_clear(expected_mean);
    if (mpq_sgn(certificate->second_moment_multiplier) <= 0) {
        (void)fail(failure, "second_moment_multiplier_must_be_positive");
        goto cleanup;
    }
    if (certificate->parseval_order == 0
        || certificate->parseval_order > MAX_PARSEVAL_ORDER) {
        (void)fail(failure, "parseval_order_out_of_range");
        goto cleanup;
    }
    if (mpq_sgn(certificate->parseval_multiplier) <= 0) {
        (void)fail(failure, "parseval_multiplier_must_be_positive");
        goto cleanup;
    }
    if (declared_cosine_count == 0
        || declared_cosine_count > MAX_COSINE_ROWS) {
        (void)fail(failure, "cosine_count_out_of_range");
        goto cleanup;
    }
    if (line_count != 7UL + declared_cosine_count) {
        (void)fail(failure, "cosine_count_does_not_match_rows");
        goto cleanup;
    }

    certificate->cosines = calloc(
        (size_t)declared_cosine_count,
        sizeof(*certificate->cosines)
    );
    if (certificate->cosines == NULL) {
        (void)fail(failure, "allocation_failure");
        goto cleanup;
    }
    for (index = 0; index < (size_t)declared_cosine_count; ++index) {
        mpq_init(certificate->cosines[index].frequency);
        mpq_init(certificate->cosines[index].multiplier);
        ++certificate->cosine_count;
    }

    for (index = 0; index < certificate->cosine_count; ++index) {
        char *frequency_text;
        char *multiplier_text;
        char *separator;
        char field_name[64];

        if (strncmp(lines[7UL + index], "cosine\t", 7UL) != 0) {
            (void)fail(failure, "malformed_cosine_row:%zu", index);
            goto cleanup;
        }
        frequency_text = lines[7UL + index] + 7UL;
        separator = strchr(frequency_text, '\t');
        if (separator == NULL || separator == frequency_text
            || separator[1] == '\0' || strchr(separator + 1UL, '\t') != NULL) {
            (void)fail(failure, "malformed_cosine_row:%zu", index);
            goto cleanup;
        }
        *separator = '\0';
        multiplier_text = separator + 1UL;

        (void)snprintf(
            field_name,
            sizeof(field_name),
            "cosine_%zu_frequency",
            index
        );
        if (!canonical_decimal_to_mpq(
            frequency_text,
            certificate->cosines[index].frequency,
            field_name,
            failure
        )) {
            goto cleanup;
        }
        (void)snprintf(
            field_name,
            sizeof(field_name),
            "cosine_%zu_multiplier",
            index
        );
        if (!canonical_decimal_to_mpq(
            multiplier_text,
            certificate->cosines[index].multiplier,
            field_name,
            failure
        )) {
            goto cleanup;
        }
        if (mpq_sgn(certificate->cosines[index].frequency) <= 0
            || mpq_cmp_ui(
                certificate->cosines[index].frequency,
                MAX_FREQUENCY,
                1
            ) > 0) {
            (void)fail(failure, "cosine_frequency_out_of_range:%zu", index);
            goto cleanup;
        }
        if (index > 0
            && mpq_cmp(
                certificate->cosines[index - 1UL].frequency,
                certificate->cosines[index].frequency
            ) >= 0) {
            (void)fail(failure, "cosine_frequencies_not_strictly_increasing");
            goto cleanup;
        }
        if (mpq_sgn(certificate->cosines[index].multiplier) <= 0) {
            (void)fail(failure, "cosine_multiplier_must_be_positive:%zu", index);
            goto cleanup;
        }
    }
    result = true;

cleanup:
    free(lines);
    free(payload);
    return result;
}

static void term_init(Term *term, mpfr_prec_t precision)
{
    mpfi_init2(term->frequency, precision);
    mpfi_init2(term->coefficient, precision);
    mpfi_init2(term->derivative_coefficient, precision);
    mpfi_init2(term->second_derivative_coefficient, precision);
    mpfi_init2(term->primitive_coefficient, precision);
}

static void term_clear(Term *term)
{
    mpfi_clear(term->frequency);
    mpfi_clear(term->coefficient);
    mpfi_clear(term->derivative_coefficient);
    mpfi_clear(term->second_derivative_coefficient);
    mpfi_clear(term->primitive_coefficient);
}

static void compiled_certificate_init(
    CompiledCertificate *compiled,
    mpfr_prec_t precision
)
{
    memset(compiled, 0, sizeof(*compiled));
    compiled->precision = precision;
    mpfi_init2(compiled->constant, precision);
    mpfi_init2(compiled->quadratic, precision);
    mpfi_init2(compiled->third_derivative_bound, precision);
}

static void compiled_certificate_clear(CompiledCertificate *compiled)
{
    size_t index;

    for (index = 0; index < compiled->initialized_terms; ++index) {
        term_clear(&compiled->terms[index]);
    }
    free(compiled->terms);
    mpfi_clear(compiled->constant);
    mpfi_clear(compiled->quadratic);
    mpfi_clear(compiled->third_derivative_bound);
}

static bool prepare_term(
    Term *term,
    mpfi_srcptr frequency,
    mpfi_srcptr coefficient,
    CompiledCertificate *compiled,
    mpfi_ptr frequency_squared,
    mpfi_ptr temporary,
    Failure *failure
)
{
    mpfi_set(term->frequency, frequency);
    mpfi_set(term->coefficient, coefficient);
    mpfi_sqr(frequency_squared, frequency);

    mpfi_mul(term->derivative_coefficient, coefficient, frequency);
    mpfi_neg(
        term->derivative_coefficient,
        term->derivative_coefficient
    );
    mpfi_mul(
        term->second_derivative_coefficient,
        coefficient,
        frequency_squared
    );
    mpfi_neg(
        term->second_derivative_coefficient,
        term->second_derivative_coefficient
    );
    mpfi_div(term->primitive_coefficient, coefficient, frequency);

    mpfi_abs(temporary, coefficient);
    mpfi_mul(temporary, temporary, frequency_squared);
    mpfi_mul(temporary, temporary, frequency);
    mpfi_add(
        compiled->third_derivative_bound,
        compiled->third_derivative_bound,
        temporary
    );

    if (!interval_is_finite(term->frequency)
        || !interval_is_finite(term->coefficient)
        || !interval_is_finite(term->derivative_coefficient)
        || !interval_is_finite(term->second_derivative_coefficient)
        || !interval_is_finite(term->primitive_coefficient)
        || !interval_is_finite(compiled->third_derivative_bound)) {
        return fail(failure, "nonfinite_compiled_term");
    }
    return true;
}

static bool compile_certificate(
    const Certificate *certificate,
    CompiledCertificate *compiled,
    Failure *failure
)
{
    mpq_t second_moment_bound;
    mpq_t rational_temporary;
    mpfi_t frequency;
    mpfi_t coefficient;
    mpfi_t temporary;
    mpfi_t temporary_two;
    mpfi_t frequency_squared;
    mpfi_t pi;
    size_t index;
    size_t term_index;
    bool result = false;

    compiled->term_count = certificate->cosine_count
        + (size_t)certificate->parseval_order;
    compiled->terms = calloc(compiled->term_count, sizeof(*compiled->terms));
    if (compiled->terms == NULL) {
        return fail(failure, "allocation_failure");
    }
    for (index = 0; index < compiled->term_count; ++index) {
        term_init(&compiled->terms[index], compiled->precision);
        ++compiled->initialized_terms;
    }

    mpq_init(second_moment_bound);
    mpq_init(rational_temporary);
    mpfi_init2(frequency, compiled->precision);
    mpfi_init2(coefficient, compiled->precision);
    mpfi_init2(temporary, compiled->precision);
    mpfi_init2(temporary_two, compiled->precision);
    mpfi_init2(frequency_squared, compiled->precision);
    mpfi_init2(pi, compiled->precision);

    mpq_mul(
        rational_temporary,
        certificate->mean_abs_max,
        certificate->mean_abs_max
    );
    mpq_div_2exp(rational_temporary, rational_temporary, 1);
    mpq_set_ui(second_moment_bound, 2, 3);
    mpq_add(
        second_moment_bound,
        second_moment_bound,
        rational_temporary
    );

    mpfi_set_ui(compiled->constant, 1);
    mpfi_set_q(temporary, second_moment_bound);
    mpfi_mul_q(
        temporary,
        temporary,
        certificate->second_moment_multiplier
    );
    mpfi_add(compiled->constant, compiled->constant, temporary);

    mpfi_set_q(temporary, certificate->parseval_multiplier);
    mpfi_div_ui(temporary, temporary, 2);
    mpfi_add(compiled->constant, compiled->constant, temporary);

    mpfi_set_q(
        compiled->quadratic,
        certificate->second_moment_multiplier
    );
    mpfi_neg(compiled->quadratic, compiled->quadratic);
    mpfi_set_ui(compiled->third_derivative_bound, 0);

    term_index = 0;
    for (index = 0; index < certificate->cosine_count; ++index) {
        mpfi_set_q(frequency, certificate->cosines[index].frequency);
        mpfi_set_q(coefficient, certificate->cosines[index].multiplier);

        mpfi_sin(temporary, frequency);
        mpfi_div(temporary, temporary, frequency);
        mpfi_sqr(temporary, temporary);
        mpfi_mul_q(
            temporary,
            temporary,
            certificate->cosines[index].multiplier
        );
        mpfi_add(compiled->constant, compiled->constant, temporary);

        mpfi_neg(coefficient, coefficient);
        if (!prepare_term(
            &compiled->terms[term_index],
            frequency,
            coefficient,
            compiled,
            frequency_squared,
            temporary_two,
            failure
        )) {
            goto cleanup;
        }
        ++term_index;
    }

    mpfi_const_pi(pi);
    mpfi_set_q(coefficient, certificate->parseval_multiplier);
    for (index = 1; index <= certificate->parseval_order; ++index) {
        mpfi_mul_ui(frequency, pi, (unsigned long)index);
        if (!prepare_term(
            &compiled->terms[term_index],
            frequency,
            coefficient,
            compiled,
            frequency_squared,
            temporary_two,
            failure
        )) {
            goto cleanup;
        }
        ++term_index;
    }

    if (term_index != compiled->term_count
        || !interval_is_finite(compiled->constant)
        || !interval_is_finite(compiled->quadratic)
        || !interval_is_finite(compiled->third_derivative_bound)
        || mpfi_is_error() != 0) {
        (void)fail(failure, "certificate_compilation_failed");
        goto cleanup;
    }
    result = true;

cleanup:
    mpq_clear(second_moment_bound);
    mpq_clear(rational_temporary);
    mpfi_clear(frequency);
    mpfi_clear(coefficient);
    mpfi_clear(temporary);
    mpfi_clear(temporary_two);
    mpfi_clear(frequency_squared);
    mpfi_clear(pi);
    return result;
}

static void workspace_init(Workspace *workspace, mpfr_prec_t precision)
{
    mpfi_init2(workspace->x, precision);
    mpfi_init2(workspace->x_squared, precision);
    mpfi_init2(workspace->value, precision);
    mpfi_init2(workspace->derivative, precision);
    mpfi_init2(workspace->second_derivative, precision);
    mpfi_init2(workspace->argument, precision);
    mpfi_init2(workspace->sine, precision);
    mpfi_init2(workspace->cosine, precision);
    mpfi_init2(workspace->temporary, precision);
    mpfi_init2(workspace->temporary_two, precision);
    mpfi_init2(workspace->radius, precision);
    mpfi_init2(workspace->error, precision);
    mpfi_init2(workspace->absolute, precision);
    mpfi_init2(workspace->symmetric_error, precision);
    mpfi_init2(workspace->x_cubed, precision);
    mpfr_init2(workspace->lower, precision);
    mpfr_init2(workspace->upper, precision);
}

static void workspace_clear(Workspace *workspace)
{
    mpfi_clear(workspace->x);
    mpfi_clear(workspace->x_squared);
    mpfi_clear(workspace->value);
    mpfi_clear(workspace->derivative);
    mpfi_clear(workspace->second_derivative);
    mpfi_clear(workspace->argument);
    mpfi_clear(workspace->sine);
    mpfi_clear(workspace->cosine);
    mpfi_clear(workspace->temporary);
    mpfi_clear(workspace->temporary_two);
    mpfi_clear(workspace->radius);
    mpfi_clear(workspace->error);
    mpfi_clear(workspace->absolute);
    mpfi_clear(workspace->symmetric_error);
    mpfi_clear(workspace->x_cubed);
    mpfr_clear(workspace->lower);
    mpfr_clear(workspace->upper);
}

static void audit_init(Audit *audit, mpfr_prec_t precision)
{
    memset(audit, 0, sizeof(*audit));
    mpq_init(audit->pending_left);
    mpq_init(audit->pending_right);
    mpfi_init2(audit->positive_integral, precision);
    mpfi_init2(audit->uncertain_integral, precision);
    mpfi_set_ui(audit->positive_integral, 0);
    mpfi_set_ui(audit->uncertain_integral, 0);
}

static void audit_clear(Audit *audit)
{
    mpq_clear(audit->pending_left);
    mpq_clear(audit->pending_right);
    mpfi_clear(audit->positive_integral);
    mpfi_clear(audit->uncertain_integral);
}

static void verification_init(
    Verification *verification,
    const CompiledCertificate *certificate,
    unsigned long max_depth,
    Failure *failure
)
{
    mpfr_prec_t precision = certificate->precision;

    memset(verification, 0, sizeof(*verification));
    verification->certificate = certificate;
    verification->failure = failure;
    verification->max_depth = max_depth;
    workspace_init(&verification->workspace, precision);
    audit_init(&verification->audit, precision);
    mpfi_init2(verification->range, precision);
    mpfi_init2(verification->antiderivative_left, precision);
    mpfi_init2(verification->antiderivative_right, precision);
    mpfi_init2(verification->contribution, precision);
    mpfi_init2(verification->charge, precision);
}

static void verification_clear(Verification *verification)
{
    workspace_clear(&verification->workspace);
    audit_clear(&verification->audit);
    mpfi_clear(verification->range);
    mpfi_clear(verification->antiderivative_left);
    mpfi_clear(verification->antiderivative_right);
    mpfi_clear(verification->contribution);
    mpfi_clear(verification->charge);
}

static bool increment_counter(
    uint64_t *counter,
    const char *counter_name,
    Failure *failure
)
{
    if (*counter == UINT64_MAX) {
        return fail(failure, "counter_overflow:%s", counter_name);
    }
    ++*counter;
    return true;
}

static bool evaluate_at_point(
    Verification *verification,
    const mpq_t point
)
{
    const CompiledCertificate *certificate = verification->certificate;
    Workspace *workspace = &verification->workspace;
    size_t index;

    mpfi_set_q(workspace->x, point);
    mpfi_sqr(workspace->x_squared, workspace->x);
    mpfi_mul(
        workspace->value,
        certificate->quadratic,
        workspace->x_squared
    );
    mpfi_add(
        workspace->value,
        workspace->value,
        certificate->constant
    );

    mpfi_mul_ui(workspace->temporary, certificate->quadratic, 2);
    mpfi_mul(
        workspace->derivative,
        workspace->temporary,
        workspace->x
    );
    mpfi_set(
        workspace->second_derivative,
        workspace->temporary
    );

    for (index = 0; index < certificate->term_count; ++index) {
        const Term *term = &certificate->terms[index];

        mpfi_mul(
            workspace->argument,
            term->frequency,
            workspace->x
        );
        mpfi_sin(workspace->sine, workspace->argument);
        mpfi_cos(workspace->cosine, workspace->argument);

        mpfi_mul(
            workspace->temporary,
            term->coefficient,
            workspace->cosine
        );
        mpfi_add(
            workspace->value,
            workspace->value,
            workspace->temporary
        );

        mpfi_mul(
            workspace->temporary,
            term->derivative_coefficient,
            workspace->sine
        );
        mpfi_add(
            workspace->derivative,
            workspace->derivative,
            workspace->temporary
        );

        mpfi_mul(
            workspace->temporary,
            term->second_derivative_coefficient,
            workspace->cosine
        );
        mpfi_add(
            workspace->second_derivative,
            workspace->second_derivative,
            workspace->temporary
        );
    }

    if (!interval_is_finite(workspace->value)
        || !interval_is_finite(workspace->derivative)
        || !interval_is_finite(workspace->second_derivative)
        || mpfi_is_error() != 0) {
        return fail(verification->failure, "nonfinite_point_evaluation");
    }
    return true;
}

static bool taylor_range(
    Verification *verification,
    const mpq_t midpoint,
    const mpq_t radius
)
{
    const CompiledCertificate *certificate = verification->certificate;
    Workspace *workspace = &verification->workspace;

    if (!evaluate_at_point(verification, midpoint)) {
        return false;
    }

    mpfi_set_q(workspace->radius, radius);
    mpfi_abs(workspace->absolute, workspace->derivative);
    mpfi_mul(
        workspace->error,
        workspace->absolute,
        workspace->radius
    );

    mpfi_sqr(workspace->temporary_two, workspace->radius);
    mpfi_abs(workspace->absolute, workspace->second_derivative);
    mpfi_mul(
        workspace->temporary,
        workspace->absolute,
        workspace->temporary_two
    );
    mpfi_div_ui(workspace->temporary, workspace->temporary, 2);
    mpfi_add(
        workspace->error,
        workspace->error,
        workspace->temporary
    );

    mpfi_mul(
        workspace->temporary,
        certificate->third_derivative_bound,
        workspace->temporary_two
    );
    mpfi_mul(
        workspace->temporary,
        workspace->temporary,
        workspace->radius
    );
    mpfi_div_ui(workspace->temporary, workspace->temporary, 6);
    mpfi_add(
        workspace->error,
        workspace->error,
        workspace->temporary
    );

    if (!interval_is_finite(workspace->error)) {
        return fail(verification->failure, "nonfinite_taylor_error");
    }
    mpfi_get_right(workspace->upper, workspace->error);
    if (mpfr_sgn(workspace->upper) < 0) {
        return fail(verification->failure, "negative_taylor_error");
    }
    mpfr_neg(workspace->lower, workspace->upper, MPFR_RNDD);
    mpfi_interv_fr(
        workspace->symmetric_error,
        workspace->lower,
        workspace->upper
    );
    mpfi_add(
        verification->range,
        workspace->value,
        workspace->symmetric_error
    );

    if (!interval_is_finite(verification->range)
        || mpfi_is_error() != 0) {
        return fail(verification->failure, "nonfinite_taylor_range");
    }
    return true;
}

static bool antiderivative(
    Verification *verification,
    mpfi_ptr output,
    const mpq_t point
)
{
    const CompiledCertificate *certificate = verification->certificate;
    Workspace *workspace = &verification->workspace;
    size_t index;

    mpfi_set_q(workspace->x, point);
    mpfi_sqr(workspace->x_squared, workspace->x);
    mpfi_mul(
        workspace->x_cubed,
        workspace->x_squared,
        workspace->x
    );

    mpfi_mul(output, certificate->constant, workspace->x);
    mpfi_mul(
        workspace->temporary,
        certificate->quadratic,
        workspace->x_cubed
    );
    mpfi_div_ui(workspace->temporary, workspace->temporary, 3);
    mpfi_add(output, output, workspace->temporary);

    for (index = 0; index < certificate->term_count; ++index) {
        const Term *term = &certificate->terms[index];

        mpfi_mul(
            workspace->argument,
            term->frequency,
            workspace->x
        );
        mpfi_sin(workspace->sine, workspace->argument);
        mpfi_mul(
            workspace->temporary,
            term->primitive_coefficient,
            workspace->sine
        );
        mpfi_add(output, output, workspace->temporary);
    }

    if (!interval_is_finite(output) || mpfi_is_error() != 0) {
        return fail(verification->failure, "nonfinite_antiderivative");
    }
    return true;
}

static bool flush_positive_run(Verification *verification)
{
    Audit *audit = &verification->audit;
    Workspace *workspace = &verification->workspace;

    if (!audit->pending_positive) {
        return true;
    }
    if (!antiderivative(
        verification,
        verification->antiderivative_left,
        audit->pending_left
    ) || !antiderivative(
        verification,
        verification->antiderivative_right,
        audit->pending_right
    )) {
        return false;
    }
    mpfi_sub(
        verification->contribution,
        verification->antiderivative_right,
        verification->antiderivative_left
    );
    if (!interval_is_finite(verification->contribution)) {
        return fail(verification->failure, "nonfinite_positive_integral");
    }
    mpfi_get_right(workspace->upper, verification->contribution);
    if (mpfr_sgn(workspace->upper) < 0) {
        return fail(
            verification->failure,
            "certified_positive_run_has_negative_integral"
        );
    }
    mpfi_add(
        audit->positive_integral,
        audit->positive_integral,
        verification->contribution
    );
    if (!interval_is_finite(audit->positive_integral)) {
        return fail(verification->failure, "nonfinite_positive_integral");
    }
    audit->pending_positive = false;
    return true;
}

static bool extend_positive_run(
    Verification *verification,
    const mpq_t left,
    const mpq_t right
)
{
    Audit *audit = &verification->audit;

    if (audit->pending_positive
        && mpq_cmp(audit->pending_right, left) != 0) {
        if (!flush_positive_run(verification)) {
            return false;
        }
    }
    if (!audit->pending_positive) {
        mpq_set(audit->pending_left, left);
        audit->pending_positive = true;
    }
    mpq_set(audit->pending_right, right);
    return true;
}

static bool add_terminal_rectangle(
    Verification *verification,
    const mpq_t left,
    const mpq_t right
)
{
    Audit *audit = &verification->audit;
    Workspace *workspace = &verification->workspace;
    mpq_t width;

    mpfi_get_right(workspace->upper, verification->range);
    if (mpfr_sgn(workspace->upper) <= 0) {
        return true;
    }

    mpq_init(width);
    mpq_sub(width, right, left);
    mpfi_set_fr(verification->charge, workspace->upper);
    mpfi_mul_q(verification->charge, verification->charge, width);
    mpq_clear(width);
    mpfi_add(
        audit->uncertain_integral,
        audit->uncertain_integral,
        verification->charge
    );
    if (!interval_is_finite(audit->uncertain_integral)) {
        return fail(verification->failure, "nonfinite_terminal_charge");
    }
    return true;
}

static bool verify_cell(
    Verification *verification,
    const mpq_t left,
    const mpq_t right,
    unsigned long depth
)
{
    Audit *audit = &verification->audit;
    Workspace *workspace = &verification->workspace;
    mpq_t midpoint;
    mpq_t radius;
    bool result = false;

    if (!increment_counter(
        &audit->visited_cells,
        "visited_cells",
        verification->failure
    )) {
        return false;
    }
    if (audit->visited_cells > MAX_VISITED_CELLS) {
        return fail(verification->failure, "visited_cell_budget_exceeded");
    }

    mpq_init(midpoint);
    mpq_init(radius);
    mpq_add(midpoint, left, right);
    mpq_div_2exp(midpoint, midpoint, 1);
    mpq_sub(radius, right, left);
    mpq_div_2exp(radius, radius, 1);

    if (!taylor_range(verification, midpoint, radius)) {
        goto cleanup;
    }
    mpfi_get_right(workspace->upper, verification->range);
    if (mpfr_sgn(workspace->upper) <= 0) {
        if (!flush_positive_run(verification)
            || !increment_counter(
                &audit->negative_cells,
                "negative_cells",
                verification->failure
            )) {
            goto cleanup;
        }
    } else {
        mpfi_get_left(workspace->lower, verification->range);
        if (mpfr_sgn(workspace->lower) >= 0) {
            if (!increment_counter(
                &audit->positive_cells,
                "positive_cells",
                verification->failure
            ) || !extend_positive_run(verification, left, right)) {
                goto cleanup;
            }
        } else if (depth >= verification->max_depth) {
            if (!flush_positive_run(verification)
                || !increment_counter(
                    &audit->terminal_cells,
                    "terminal_cells",
                    verification->failure
                )
                || !add_terminal_rectangle(verification, left, right)) {
                goto cleanup;
            }
        } else {
            if (!increment_counter(
                &audit->split_cells,
                "split_cells",
                verification->failure
            )) {
                goto cleanup;
            }
            if (depth + 1UL > audit->max_depth_seen) {
                audit->max_depth_seen = depth + 1UL;
            }
            if (!verify_cell(verification, left, midpoint, depth + 1UL)
                || !verify_cell(
                    verification,
                    midpoint,
                    right,
                    depth + 1UL
                )) {
                goto cleanup;
            }
        }
    }
    result = true;

cleanup:
    mpq_clear(midpoint);
    mpq_clear(radius);
    return result;
}

static void print_mpfr_value(
    const char *key,
    mpfr_srcptr value,
    mpfr_rnd_t rounding
)
{
    if (mpfr_zero_p(value) != 0) {
        printf("%s=0\n", key);
        return;
    }
    printf("%s=", key);
    (void)mpfr_out_str(stdout, 10, OUTPUT_DIGITS, value, rounding);
    putchar('\n');
}

static void print_mpq_value(const char *key, const mpq_t value)
{
    printf("%s=", key);
    (void)mpq_out_str(stdout, 10, value);
    putchar('\n');
}

static bool report_result(
    const Certificate *certificate,
    const CompiledCertificate *compiled,
    const Verification *verification,
    unsigned long initial_cells,
    bool *certified_out,
    Failure *failure
)
{
    mpfi_t positive_doubled;
    mpfi_t uncertain_doubled;
    mpfi_t denominator;
    mpfi_t target_denominator_interval;
    mpfi_t margin;
    mpq_t target_denominator;
    mpfr_t positive_upper;
    mpfr_t uncertain_upper;
    mpfr_t denominator_upper;
    mpfr_t target_denominator_lower;
    mpfr_t margin_lower;
    bool certified;

    mpfi_init2(positive_doubled, compiled->precision);
    mpfi_init2(uncertain_doubled, compiled->precision);
    mpfi_init2(denominator, compiled->precision);
    mpfi_init2(target_denominator_interval, compiled->precision);
    mpfi_init2(margin, compiled->precision);
    mpq_init(target_denominator);
    mpfr_init2(positive_upper, compiled->precision);
    mpfr_init2(uncertain_upper, compiled->precision);
    mpfr_init2(denominator_upper, compiled->precision);
    mpfr_init2(target_denominator_lower, compiled->precision);
    mpfr_init2(margin_lower, compiled->precision);

    mpfi_mul_ui(
        positive_doubled,
        verification->audit.positive_integral,
        2
    );
    mpfi_mul_ui(
        uncertain_doubled,
        verification->audit.uncertain_integral,
        2
    );
    mpfi_add(denominator, positive_doubled, uncertain_doubled);
    mpq_inv(target_denominator, certificate->target);
    mpfi_set_q(target_denominator_interval, target_denominator);
    mpfi_sub(margin, target_denominator_interval, denominator);

    if (!interval_is_finite(positive_doubled)
        || !interval_is_finite(uncertain_doubled)
        || !interval_is_finite(denominator)
        || !interval_is_finite(target_denominator_interval)
        || !interval_is_finite(margin)
        || mpfi_is_error() != 0) {
        (void)fail(failure, "nonfinite_final_result");
        goto failure;
    }

    mpfi_get_right(positive_upper, positive_doubled);
    mpfi_get_right(uncertain_upper, uncertain_doubled);
    mpfi_get_right(denominator_upper, denominator);
    mpfi_get_left(
        target_denominator_lower,
        target_denominator_interval
    );
    mpfi_get_left(margin_lower, margin);
    certified = mpfr_cmp_q(denominator_upper, target_denominator) < 0;

    printf("backend=mpfi-c\n");
    printf("mpfi_version=%s\n", mpfi_get_version());
    printf("certificate_schema=%s\n", CERTIFICATE_SCHEMA);
    printf("precision_bits=%lu\n", (unsigned long)compiled->precision);
    printf("initial_cells=%lu\n", initial_cells);
    printf("max_depth=%lu\n", verification->max_depth);
    printf("integration_half_interval=0,2\n");
    printf("evenness_factor=2\n");
    printf("target=%s\n", certificate->target_text);
    printf("cosine_rows=%zu\n", certificate->cosine_count);
    printf("parseval_order=%lu\n", certificate->parseval_order);
    printf(
        "visited_cells=%llu\n",
        (unsigned long long)verification->audit.visited_cells
    );
    printf(
        "negative_cells=%llu\n",
        (unsigned long long)verification->audit.negative_cells
    );
    printf(
        "positive_cells=%llu\n",
        (unsigned long long)verification->audit.positive_cells
    );
    printf(
        "split_cells=%llu\n",
        (unsigned long long)verification->audit.split_cells
    );
    printf(
        "terminal_cells=%llu\n",
        (unsigned long long)verification->audit.terminal_cells
    );
    printf(
        "max_depth_seen=%lu\n",
        verification->audit.max_depth_seen
    );
    print_mpfr_value(
        "positive_antiderivative_upper",
        positive_upper,
        MPFR_RNDU
    );
    print_mpfr_value(
        "uncertain_rectangle_upper",
        uncertain_upper,
        MPFR_RNDU
    );
    print_mpfr_value(
        "denominator_upper",
        denominator_upper,
        MPFR_RNDU
    );
    print_mpq_value("target_denominator_exact", target_denominator);
    print_mpfr_value(
        "target_denominator_lower",
        target_denominator_lower,
        MPFR_RNDD
    );
    print_mpfr_value(
        "denominator_margin_lower",
        margin_lower,
        MPFR_RNDD
    );
    printf("certified=%s\n", certified ? "true" : "false");

    *certified_out = certified;
    mpfi_clear(positive_doubled);
    mpfi_clear(uncertain_doubled);
    mpfi_clear(denominator);
    mpfi_clear(target_denominator_interval);
    mpfi_clear(margin);
    mpq_clear(target_denominator);
    mpfr_clear(positive_upper);
    mpfr_clear(uncertain_upper);
    mpfr_clear(denominator_upper);
    mpfr_clear(target_denominator_lower);
    mpfr_clear(margin_lower);
    return true;

failure:
    mpfi_clear(positive_doubled);
    mpfi_clear(uncertain_doubled);
    mpfi_clear(denominator);
    mpfi_clear(target_denominator_interval);
    mpfi_clear(margin);
    mpq_clear(target_denominator);
    mpfr_clear(positive_upper);
    mpfr_clear(uncertain_upper);
    mpfr_clear(denominator_upper);
    mpfr_clear(target_denominator_lower);
    mpfr_clear(margin_lower);
    return false;
}

static void print_failure(const char *status, const Failure *failure)
{
    fprintf(stderr, "status=%s\n", status);
    fprintf(
        stderr,
        "error=%s\n",
        failure->text[0] == '\0' ? "unspecified_failure" : failure->text
    );
}

static int usage(const char *program)
{
    fprintf(
        stderr,
        "usage: %s certificate.tsv [precision_bits=256] "
        "[initial_cells=4096] [max_depth=16]\n",
        program
    );
    return 2;
}

int main(int argc, char **argv)
{
    Failure failure = {{0}};
    Certificate certificate;
    CompiledCertificate compiled;
    Verification verification;
    unsigned long precision_bits = 256UL;
    unsigned long initial_cells = 4096UL;
    unsigned long max_depth = 16UL;
    mpq_t left;
    mpq_t right;
    unsigned long index;
    bool verification_initialized = false;
    bool certified = false;
    int exit_code;

    if (argc < 2 || argc > 5) {
        return usage(argv[0]);
    }
    if (argc >= 3
        && !canonical_unsigned_long(
            argv[2],
            &precision_bits,
            "precision_bits",
            &failure
        )) {
        print_failure("argument_error", &failure);
        return 2;
    }
    if (argc >= 4
        && !canonical_unsigned_long(
            argv[3],
            &initial_cells,
            "initial_cells",
            &failure
        )) {
        print_failure("argument_error", &failure);
        return 2;
    }
    if (argc >= 5
        && !canonical_unsigned_long(
            argv[4],
            &max_depth,
            "max_depth",
            &failure
        )) {
        print_failure("argument_error", &failure);
        return 2;
    }
    if (precision_bits < MIN_PRECISION_BITS
        || precision_bits > MAX_PRECISION_BITS) {
        (void)fail(&failure, "precision_bits_out_of_range");
        print_failure("argument_error", &failure);
        return 2;
    }
    if (initial_cells == 0 || initial_cells > MAX_INITIAL_CELLS) {
        (void)fail(&failure, "initial_cells_out_of_range");
        print_failure("argument_error", &failure);
        return 2;
    }
    if (max_depth > MAX_BISECTION_DEPTH) {
        (void)fail(&failure, "max_depth_out_of_range");
        print_failure("argument_error", &failure);
        return 2;
    }

    certificate_init(&certificate);
    if (!parse_certificate(argv[1], &certificate, &failure)) {
        print_failure("parse_failure", &failure);
        certificate_clear(&certificate);
        return 2;
    }

    mpfi_reset_error();
    compiled_certificate_init(
        &compiled,
        (mpfr_prec_t)precision_bits
    );
    if (!compile_certificate(&certificate, &compiled, &failure)) {
        print_failure("compilation_failure", &failure);
        compiled_certificate_clear(&compiled);
        certificate_clear(&certificate);
        return 3;
    }

    verification_init(&verification, &compiled, max_depth, &failure);
    verification_initialized = true;
    mpq_init(left);
    mpq_init(right);
    exit_code = 3;

    for (index = 0; index < initial_cells; ++index) {
        mpq_set_ui(left, 2UL * index, initial_cells);
        mpq_set_ui(right, 2UL * (index + 1UL), initial_cells);
        if (!verify_cell(&verification, left, right, 0)) {
            print_failure("verification_failure", &failure);
            goto cleanup;
        }
    }
    if (!flush_positive_run(&verification)) {
        print_failure("verification_failure", &failure);
        goto cleanup;
    }
    if (!report_result(
        &certificate,
        &compiled,
        &verification,
        initial_cells,
        &certified,
        &failure
    )) {
        print_failure("verification_failure", &failure);
        goto cleanup;
    }
    exit_code = certified ? 0 : 1;

cleanup:
    mpq_clear(left);
    mpq_clear(right);
    if (verification_initialized) {
        verification_clear(&verification);
    }
    compiled_certificate_clear(&compiled);
    certificate_clear(&certificate);
    return exit_code;
}
