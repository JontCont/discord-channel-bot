import {
  Navigate,
  Outlet,
  createRootRoute,
  createRoute,
  createRouter,
} from '@tanstack/react-router'
import { AuthenticatedLayout } from './ui/AuthenticatedLayout'
import { GuildPicker } from './ui/GuildPicker'
import { LoginScreen } from './ui/LoginScreen'
import { SettingsPage } from './ui/SettingsPage'
import { NotFound } from './ui/States'

const rootRoute = createRootRoute({
  component: Outlet,
  notFoundComponent: NotFound,
})

const indexRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/',
  component: () => <Navigate to="/guilds" replace />,
})

const loginRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/login',
  component: LoginScreen,
})

const authenticatedRoute = createRoute({
  getParentRoute: () => rootRoute,
  id: 'authenticated',
  component: AuthenticatedLayout,
})

const guildsRoute = createRoute({
  getParentRoute: () => authenticatedRoute,
  path: '/guilds',
  component: GuildPicker,
})

const settingsRoute = createRoute({
  getParentRoute: () => authenticatedRoute,
  path: '/guilds/$guildId/settings',
  component: SettingsPage,
})

const routeTree = rootRoute.addChildren([
  indexRoute,
  loginRoute,
  authenticatedRoute.addChildren([guildsRoute, settingsRoute]),
])

export const router = createRouter({ routeTree })

declare module '@tanstack/react-router' {
  interface Register {
    router: typeof router
  }
}