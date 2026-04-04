# Vue 3 Testing Best Practices (2026)

**Date:** 2026-04-04
**Tech Stack:** Vue 3 + Vite + TypeScript + Pinia + Vue Router + Supabase

---

## 1. Testing Framework: Vitest vs Jest

### **Recommendation: Vitest**

**Why Vitest over Jest:**
- Native Vite integration → instant startup, HMR, same config as build
- Native ESM support → no babel transpilation needed
- Built-in mocking (vi.fn(), vi.mock()) → no separate mocking library
- Native TypeScript support → no Babel transformers
- Same test syntax as Jest → easy migration from Jest
- ~10x faster than Jest for watch mode

**Setup Pattern:**
```typescript
// vite.config.ts
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath } from 'node:url'

export default defineConfig({
  plugins: [vue()],
  test: {
    globals: true,
    environment: 'jsdom',
    include: ['src/**/*.{test,spec}.{js,ts}'],
    setupFiles: './src/tests/setup.ts',
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      exclude: ['node_modules/', 'src/tests/']
    }
  }
})
```

**Package Dependencies:**
```json
{
  "devDependencies": {
    "@vitest/ui": "^1.1.0",
    "vitest": "^1.1.0",
    "jsdom": "^24.0.0"
  }
}
```

**Test Configuration:**
```typescript
// src/tests/setup.ts
import { vi } from 'vitest'
import { config } from '@vue/test-utils'
import '@testing-library/jest-dom/vitest'

config.global.mocks = {
  $t: (key: string) => key
}

// Mock Supabase globally
vi.mock('@supabase/supabase-js', () => ({
  createClient: vi.fn(() => ({
    auth: {
      getSession: vi.fn().mockResolvedValue({ data: { session: null }, error: null }),
      getUser: vi.fn().mockResolvedValue({ data: { user: null }, error: null }),
      signUp: vi.fn().mockResolvedValue({ data: { user: null }, error: null }),
      signInWithPassword: vi.fn().mockResolvedValue({ data: { session: null }, error: null }),
      signOut: vi.fn().mockResolvedValue({ error: null }),
    },
    from: vi.fn(() => ({
      select: vi.fn(() => ({
        data: [],
        error: null
      })),
      insert: vi.fn(() => ({
        data: [],
        error: null
      })),
      update: vi.fn(() => ({
        data: [],
        error: null
      })),
      delete: vi.fn(() => ({
        data: [],
        error: null
      })),
    })),
  }))
})
```

---

## 2. Component Testing: Vue Test Utils (@vue/test-utils)

### **Recommendation: Vue Testing Library (wrapper around Test Utils)**

**Why Vue Testing Library over Vue Test Utils:**
- User-centric testing (tests what users see/interact with)
- Simpler API, less magic, easier to read
- Better documentation
- More aligned with accessibility best practices

**Setup Pattern:**
```typescript
// install globally
// src/tests/setup.ts
import '@testing-library/jest-dom'
```

**Test Component:**
```typescript
// src/components/UserProfile.spec.ts
import { mount } from '@vue/test-utils'
import UserProfile from './UserProfile.vue'

describe('UserProfile.vue', () => {
  it('renders user name when logged in', () => {
    const wrapper = mount(UserProfile, {
      props: {
        user: { name: 'John Doe', email: 'john@example.com' }
      }
    })

    expect(wrapper.text()).toContain('John Doe')
    expect(wrapper.text()).toContain('john@example.com')
  })

  it('shows login button when not logged in', async () => {
    const wrapper = mount(UserProfile, {
      props: { user: null }
    })

    const loginButton = wrapper.getByRole('button', { name: 'Login' })
    await loginButton.click()
    expect(wrapper.emitted()).toHaveProperty('login')
  })

  it('emits logout event when logout clicked', async () => {
    const wrapper = mount(UserProfile, {
      props: {
        user: { name: 'John Doe' },
        isAuthenticated: true
      }
    })

    const logoutButton = wrapper.getByRole('button', { name: 'Logout' })
    await logoutButton.click()
    expect(wrapper.emitted()).toHaveProperty('logout')
  })
})
```

**What to Test:**
- Render output (text, attributes, classes)
- User interactions (clicks, inputs)
- Props passed correctly
- Emits events correctly
- Component behavior (not implementation details)

**What NOT to Test:**
- Internal implementation details (private methods)
- Prop validation (Vue handles this)
- CSS classes (unless accessibility critical)
- Implementation logic hidden behind props
- Lifecycle hooks (unless testing side effects)

---

## 3. E2E Testing: Playwright vs Cypress

### **Recommendation: Playwright**

**Why Playwright over Cypress:**
- Faster execution (parallel runs out-of-box)
- Better reliability (auto-wait, retry on failure)
- Built-in codegen for test generation
- Multi-browser support (Chrome, Firefox, WebKit, Electron)
- Better TypeScript support
- More active development
- Single file for all browsers (no separate Cypress config)

**Setup Pattern:**
```typescript
// playwright.config.ts
import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',
  use: {
    baseURL: 'http://localhost:5173',
    trace: 'on-first-retry',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:5173',
    reuseExistingServer: !process.env.CI,
  },
})
```

**Package Dependencies:**
```json
{
  "devDependencies": {
    "@playwright/test": "^1.40.0"
  }
}
```

**Test Example:**
```typescript
// e2e/auth-flow.spec.ts
import { test, expect } from '@playwright/test'

test.describe('Authentication Flow', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
  })

  test('should login with Google OAuth', async ({ page }) => {
    // Mock Google OAuth redirect
    await page.route('**/api/auth/google', async route => {
      await route.fulfill({
        status: 302,
        headers: { Location: '/dashboard' }
      })
    })

    await page.click('text=Sign in with Google')
    await page.waitForURL('/dashboard')
    expect(page).toHaveURL('/dashboard')
  })

  test('should display error on invalid credentials', async ({ page }) => {
    await page.fill('[name="email"]', 'invalid@example.com')
    await page.fill('[name="password"]', 'wrong-password')
    await page.click('button[type="submit"]')

    await expect(page.locator('.error-message')).toBeVisible()
    await expect(page.locator('.error-message')).toHaveText('Invalid credentials')
  })
})
```

**What to Test:**
- Full user flows (end-to-end workflows)
- Cross-browser behavior
- Critical user paths
- Error handling in real browser
- Third-party integrations (OAuth, API)

**What NOT to Test:**
- Unit test logic (use Vitest for this)
- Component rendering details
- Performance (use Lighthouse)
- Styling (use Storybook for previewing)

---

## 4. Testing Pinia Stores

### **Recommendation: Vitest + Pinia testing utilities**

**Why Not to Use Mocks:**
- Don't mock stores directly
- Test real store logic in isolation
- Mock only external dependencies (API calls, auth)

**Setup Pattern:**
```typescript
// src/stores/user.spec.ts
import { setActivePinia, createPinia } from 'pinia'
import { useUserStore } from './user'

describe('useUserStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('sets user on login', async () => {
    const store = useUserStore()
    const mockUser = { id: 1, name: 'John', email: 'john@example.com' }

    // Mock Supabase auth
    const mockSupabase = {
      auth: {
        signInWithPassword: vi.fn().mockResolvedValue({
          data: { session: { user: mockUser } },
          error: null
        })
      }
    }

    await store.login('john@example.com', 'password')
    expect(store.user).toEqual(mockUser)
    expect(mockSupabase.auth.signInWithPassword).toHaveBeenCalled()
  })

  it('clears user on logout', () => {
    const store = useUserStore()
    store.user = mockUser

    store.logout()
    expect(store.user).toBeNull()
  })

  it('computes fullName based on first and last name', () => {
    const store = useUserStore()
    store.firstName = 'John'
    store.lastName = 'Doe'

    expect(store.fullName).toBe('John Doe')
  })
})
```

**What to Test:**
- Actions (login, logout, update)
- Computed properties
- Side effects (API calls, local storage)
- State changes over time
- Error handling

**What NOT to Test:**
- Component interaction with store (test in component)
- Implementation details
- Private state (expose via getters/actions)

---

## 5. Testing Composables (Composition API)

### **Recommendation: renderHook from Vue Test Utils**

**Why renderHook:**
- Tests composables in isolation (no component overhead)
- Focus on return values and side effects
- Proper isolation of dependencies

**Setup Pattern:**
```typescript
// src/composables/useAuth.spec.ts
import { renderHook, waitFor } from '@vue/test-utils'
import { useAuth } from './useAuth'

vi.mock('@supabase/supabase-js')

describe('useAuth', () => {
  it('returns user state', () => {
    const { result } = renderHook(() => useAuth())
    expect(result.value.user).toBeNull()
    expect(result.value.isAuthenticated).toBe(false)
  })

  it('updates user after login', async () => {
    const mockUser = { id: 1, name: 'John' }
    const mockSession = { user: mockUser }

    renderHook(() => useAuth())

    // Mock login success
    await waitFor(() => {
      expect(result.value.user).toEqual(mockUser)
    })
  })

  it('handles login error', async () => {
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

    await renderHook(() => useAuth()).result.value.login('invalid', 'pass')

    expect(consoleSpy).toHaveBeenCalledWith(expect.any(Error))

    consoleSpy.mockRestore()
  })
})
```

**What to Test:**
- Return values
- Reactive state updates
- Side effects (API calls, localStorage)
- Lifecycle hooks (mounted, unmounted)
- Dependencies and composition

**What NOT to Test:**
- Component rendering (test component)
- User interactions (test via component)
- CSS styles (not composables)

---

## 6. Testing Vue Router Integration

### **Recommendation: Vitest with Vue Router mocking**

**Setup Pattern:**
```typescript
// src/router.spec.ts
import { createMemoryHistory, createRouter } from 'vue-router'
import routes from '@/router'

describe('Router', () => {
  it('navigates to dashboard when authenticated', async () => {
    const router = createRouter({
      history: createMemoryHistory(),
      routes
    })

    // Mock auth state
    vi.spyOn(useAuthStore, 'getters').mockReturnValue({
      isAuthenticated: true
    })

    await router.push('/dashboard')
    await router.isReady()

    expect(router.currentRoute.value.path).toBe('/dashboard')
  })

  it('redirects to login when accessing protected route unauthenticated', async () => {
    const router = createRouter({
      history: createMemoryHistory(),
      routes
    })

    vi.spyOn(useAuthStore, 'getters').mockReturnValue({
      isAuthenticated: false
    })

    await router.push('/dashboard')
    await router.isReady()

    expect(router.currentRoute.value.path).toBe('/login')
  })

  it('navigates home from login when authenticated', async () => {
    const router = createRouter({
      history: createMemoryHistory(),
      routes
    })

    vi.spyOn(useAuthStore, 'getters').mockReturnValue({
      isAuthenticated: true
    })

    await router.push('/login')
    await router.isReady()

    expect(router.currentRoute.value.path).toBe('/')
  })
})
```

**What to Test:**
- Route navigation
- Route guards (auth checks)
- Redirects
- Dynamic routes
- 404 handling

**What NOT to Test:**
- Component rendering (test components)
- Action completion (test via component)

---

## 7. Mocking Strategies

### **API Mocking (Supabase)**
```typescript
// src/tests/setup.ts (already shown in #1)

// Individual mock (example)
vi.mock('@/services/api', () => ({
  api: {
    getUser: vi.fn().mockResolvedValue({ data: { id: 1, name: 'John' } }),
    updateUser: vi.fn().mockResolvedValue({ data: { id: 1, name: 'Jane' } })
  }
}))
```

### **Auth Mocking**
```typescript
// Mock specific auth methods
const mockSupabase = {
  auth: {
    signInWithPassword: vi.fn().mockResolvedValue({
      data: { session: { user: { id: 1, email: 'john@example.com' } } },
      error: null
    }),
    signOut: vi.fn().mockResolvedValue({ error: null }),
    getUser: vi.fn().mockResolvedValue({
      data: { user: { id: 1, email: 'john@example.com' } },
      error: null
    })
  }
}

vi.mock('@supabase/supabase-js', () => ({
  createClient: vi.fn(() => mockSupabase)
}))
```

### **Router Mocking**
```typescript
// Mock router push
const router = {
  push: vi.fn(),
  replace: vi.fn(),
  go: vi.fn(),
  back: vi.fn()
}

vi.mock('vue-router', () => ({
  useRoute: vi.fn(() => ({ params: {}, query: {} })),
  useRouter: vi.fn(() => router)
}))
```

### **Global Mocks**
```typescript
// Use global mocks for things you don't want to test
config.global.mocks = {
  $t: (key: string) => key,
  $route: { params: {}, query: {} },
  $router: router
}
```

---

## 8. Coverage Tools and Targets

### **Recommendation: Vitest V8 Coverage**

**Setup:**
```typescript
// vite.config.ts
test: {
  coverage: {
    provider: 'v8',
    reporter: ['text', 'json', 'html'],
    lines: 70,
    functions: 70,
    branches: 70,
    statements: 70,
    exclude: [
      'node_modules/',
      'src/tests/',
      '**/*.spec.ts',
      '**/*.test.ts',
      '**/dist/',
      '**/types/',
      '**/utils/constants.ts'
    ]
  }
}
```

**Package Dependencies:**
```json
{
  "devDependencies": {
    "@vitest/coverage-v8": "^1.1.0"
  }
}
```

**Running Coverage:**
```bash
npm run test:coverage
```

**Coverage Targets (2026 Best Practice):**
- **Overall: 70-80%**
- **Critical paths (auth, data fetching): 90-100%**
- **Utility functions: 80-90%**
- **Components: 60-70%** (don't over-test components, focus on integration)
- **Storybook components: 40-50%** (not critical)

**What NOT to Cover:**
- Boilerplate files (auto-generated)
- Configuration files
- Third-party libraries (exclude in coverage config)
- CSS files
- Build artifacts

**Coverage Strategy:**
- **High coverage** on business logic, stores, composables
- **Medium coverage** on components (user interaction focus)
- **Low coverage** on third-party integration points
- **Coverage gates**: Fail CI if below target

---

## Test Structure

```
src/
├── components/           # Component tests
│   └── **/*.spec.ts
├── composables/          # Composable tests
│   └── **/*.spec.ts
├── stores/               # Store tests
│   └── **/*.spec.ts
├── router/               # Router tests
│   └── **/*.spec.ts
├── services/             # API service tests
│   └── **/*.spec.ts
└── tests/
    └── setup.ts         # Global test setup

e2e/                       # End-to-end tests
└── **/*.spec.ts
```

**File Naming:**
- Components: `ComponentName.spec.ts` or `ComponentName.test.ts`
- Composables: `useComposable.spec.ts` or `useComposable.test.ts`
- Stores: `storeName.spec.ts` or `storeName.test.ts`
- E2E: `feature-name.spec.ts`

---

## Running Tests

```json
{
  "scripts": {
    "test": "vitest",
    "test:run": "vitest run",
    "test:ui": "vitest --ui",
    "test:coverage": "vitest run --coverage",
    "test:e2e": "playwright test",
    "test:e2e:ui": "playwright test --ui"
  }
}
```

**Watch Mode:** `npm run test` (default)
**Run once:** `npm run test:run`
**UI Mode:** `npm run test:ui`
**Coverage:** `npm run test:coverage`

---

## Testing Philosophy

### **YAGNI / KISS / DRY**
- Test what users need, not implementation details
- Keep tests simple and readable
- Don't duplicate test logic (use helpers)

### **What to Test**
- User interactions and workflows
- Business logic in stores/composables
- Critical error handling
- Route navigation and guards

### **What NOT to Test**
- Private methods
- CSS styles
- Implementation details
- Boilerplate code
- Third-party libraries (unless behavior critical)

---

## Unresolved Questions

1. **Should we use Vue Testing Library or Vue Test Utils?**
   - Recommendation: Vue Testing Library (wrapper around Test Utils)
   - Consider: Team familiarity, project complexity

2. **What E2E testing coverage target?**
   - Recommendation: 50-60% for critical user flows only
   - Not full app coverage (too brittle)

3. **Should we implement snapshot testing?**
   - Recommendation: Use sparingly, prefer description-based tests
   - Snapshots are easy to overuse and hide changes

4. **Mock Supabase globally or per-test?**
   - Recommendation: Global mock for auth, per-test for API calls
   - More control when testing specific scenarios

---

## Sources

- [Vue Test Utils Documentation](https://test-utils.vuejs.org/guide/)
- [Vue Testing Library Documentation](https://testing-library.com/docs/vue-testing-library/intro/)
- [Vitest Documentation](https://vitest.dev/)
- [Playwright Documentation](https://playwright.dev/)
- [Pinia Documentation](https://pinia.vuejs.org/core/introduction.html#testing)
- [Vue 3 Official Documentation](https://vuejs.org/)
