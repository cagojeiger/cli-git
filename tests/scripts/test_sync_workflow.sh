#!/bin/bash
# Test script for mirror sync workflow

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

# Utility functions
info() {
    echo -e "${YELLOW}[INFO]${NC} $1"
}

success() {
    echo -e "${GREEN}[PASS]${NC} $1"
    ((TESTS_PASSED++))
}

fail() {
    echo -e "${RED}[FAIL]${NC} $1"
    ((TESTS_FAILED++))
}

# Create test environment
setup_test_env() {
    info "Setting up test environment..."

    # Create temporary directory
    TEST_DIR=$(mktemp -d -t mirror-sync-test-XXXXXX)
    cd "$TEST_DIR"

    # Create upstream repository
    mkdir upstream
    cd upstream
    git init --quiet
    echo "# Upstream Project" > README.md
    echo "print('hello world')" > main.py
    mkdir -p .github/workflows
    echo "name: CI" > .github/workflows/ci.yml
    echo "name: Operator" > .github/workflows/operator.yml
    echo "name: Registry Push" > .github/workflows/registry-push.yml
    git add .
    git commit -m "Initial upstream commit" --quiet
    cd ..

    # Create mirror repository
    git clone upstream mirror --quiet
    cd mirror

    # Add mirror-specific files
    echo "# 한국어 문서" > README-ko.md
    mkdir -p docs
    echo "# Mirror Documentation" > docs/mirror-guide.md
    echo "#!/bin/bash" > custom-script.sh
    chmod +x custom-script.sh

    git add .
    git commit -m "Add mirror-specific files" --quiet

    cd "$TEST_DIR"
    info "Test environment ready at: $TEST_DIR"
}

# Test 1: Basic sync preserves mirror files
test_basic_sync() {
    info "Test 1: Basic sync preserves mirror-only files"

    cd "$TEST_DIR/mirror"

    # Simulate upstream changes
    cd "$TEST_DIR/upstream"
    echo "print('updated')" > main.py
    echo "New upstream file" > new_file.txt
    git add .
    git commit -m "Update upstream" --quiet

    cd "$TEST_DIR/mirror"

    # Run sync logic (simplified version)
    git remote add upstream ../upstream || true
    git fetch upstream --quiet

    # Find mirror-only files
    comm -23 <(git ls-files | sort) \
             <(git ls-tree -r upstream/master --name-only | sort) \
             > mirror-only-files.txt

    # Backup mirror files
    mkdir -p backup
    while IFS= read -r file; do
        if [ -f "$file" ]; then
            mkdir -p "backup/$(dirname "$file")"
            cp "$file" "backup/$file"
        fi
    done < mirror-only-files.txt

    # Reset to upstream
    git reset --hard upstream/master --quiet

    # Restore mirror files
    while IFS= read -r file; do
        if [ -f "backup/$file" ]; then
            mkdir -p "$(dirname "$file")"
            cp "backup/$file" "$file"
        fi
    done < mirror-only-files.txt

    # Remove unwanted files
    rm -f .github/workflows/operator.yml
    rm -f .github/workflows/registry-push.yml

    # Verify results
    if [ -f "README-ko.md" ] && [ -f "docs/mirror-guide.md" ] && [ -f "custom-script.sh" ]; then
        success "Mirror-only files preserved"
    else
        fail "Mirror-only files lost"
    fi

    if [ -f "new_file.txt" ] && grep -q "updated" main.py; then
        success "Upstream changes applied"
    else
        fail "Upstream changes not applied"
    fi

    if [ ! -f ".github/workflows/operator.yml" ] && [ ! -f ".github/workflows/registry-push.yml" ]; then
        success "Unwanted upstream files removed"
    else
        fail "Unwanted upstream files still exist"
    fi
}

# Test 2: Handle files with spaces and special characters
test_special_filenames() {
    info "Test 2: Handle files with special characters"

    cd "$TEST_DIR/mirror"

    # Add files with special names
    echo "content" > "file with spaces.txt"
    echo "content" > "file-with-dash.txt"
    echo "content" > "file_with_underscore.txt"
    mkdir -p "directory with spaces"
    echo "content" > "directory with spaces/nested file.txt"

    git add .
    git commit -m "Add special files" --quiet

    # Run sync process
    comm -23 <(git ls-files | sort) \
             <(git ls-tree -r upstream/master --name-only | sort) \
             > mirror-only-files.txt

    # Check if special files are detected
    if grep -q "file with spaces.txt" mirror-only-files.txt && \
       grep -q "directory with spaces/nested file.txt" mirror-only-files.txt; then
        success "Special filenames detected correctly"
    else
        fail "Special filenames not detected"
    fi
}

# Test 3: Empty mirror-only files scenario
test_no_mirror_files() {
    info "Test 3: Handle case with no mirror-only files"

    # Create a new mirror that's identical to upstream
    cd "$TEST_DIR"
    rm -rf mirror-empty
    git clone upstream mirror-empty --quiet
    cd mirror-empty

    # Run sync logic
    git remote add upstream ../upstream || true
    git fetch upstream --quiet

    comm -23 <(git ls-files | sort) \
             <(git ls-tree -r upstream/master --name-only | sort) \
             > mirror-only-files.txt

    if [ ! -s mirror-only-files.txt ]; then
        success "Empty mirror-only files handled correctly"
    else
        fail "Incorrectly detected mirror-only files"
    fi
}

# Test 4: Conflicting file names
test_conflicting_names() {
    info "Test 4: Handle conflicting file names between upstream and mirror"

    cd "$TEST_DIR/mirror"

    # Mirror has a file that upstream will also add
    echo "mirror version" > conflict.txt
    git add conflict.txt
    git commit -m "Add conflict.txt in mirror" --quiet

    # Upstream adds same file
    cd "$TEST_DIR/upstream"
    echo "upstream version" > conflict.txt
    git add conflict.txt
    git commit -m "Add conflict.txt in upstream" --quiet

    cd "$TEST_DIR/mirror"
    git fetch upstream --quiet

    # After sync, upstream version should win
    git reset --hard upstream/master --quiet

    if grep -q "upstream version" conflict.txt; then
        success "Conflicting files handled correctly (upstream wins)"
    else
        fail "Conflicting files not handled correctly"
    fi
}

# Main test runner
main() {
    echo "=== Mirror Sync Workflow Tests ==="

    setup_test_env

    test_basic_sync
    test_special_filenames
    test_no_mirror_files
    test_conflicting_names

    # Summary
    echo
    echo "=== Test Summary ==="
    echo -e "Tests passed: ${GREEN}$TESTS_PASSED${NC}"
    echo -e "Tests failed: ${RED}$TESTS_FAILED${NC}"

    # Cleanup
    if [ -z "${KEEP_TEST_ENV}" ]; then
        info "Cleaning up test environment..."
        rm -rf "$TEST_DIR"
    else
        info "Test environment kept at: $TEST_DIR"
    fi

    # Exit with appropriate code
    if [ $TESTS_FAILED -eq 0 ]; then
        exit 0
    else
        exit 1
    fi
}

# Run tests
main "$@"
