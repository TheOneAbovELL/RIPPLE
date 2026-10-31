"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useId, useState } from "react";
import type { ReactNode } from "react";

import { useSession } from "@/auth/SessionProvider";

import { BrandMark } from "./BrandMark";
import { Loading } from "./LoadState";

export const HOME = "/home/";

/** Navigation by what the student wants to do (ADR-0130): today's work, telling Ripple
 * something, and looking at what it knows. */
interface NavItem {
  href: string;
  label: string;
}

export const NAV_GROUPS: readonly { label: string; items: readonly NavItem[] }[] = [
  {
    label: "Today",
    items: [
      { href: HOME, label: "Home" },
      { href: "/questions/", label: "Questions" },
      { href: "/recommendations/", label: "Recommendations" },
    ],
  },
  {
    label: "Tell Ripple",
    items: [
      { href: "/tell/", label: "Say what changed" },
      { href: "/openings/", label: "Add an opening" },
      { href: "/resume/", label: "Resume" },
    ],
  },
  {
    label: "What Ripple knows",
    items: [
      { href: "/memories/", label: "Beliefs" },
      { href: "/map/", label: "Map" },
    ],
  },
  {
    label: "You",
    items: [{ href: "/account/", label: "Account and Telegram" }],
  },
];

export const NAV = NAV_GROUPS.flatMap((group) => group.items);

interface ShellProps {
  title: string;
  /** One sentence under the title saying what the page is for. */
  lede?: ReactNode;
  children: ReactNode;
}

function isCurrent(pathname: string | null, href: string): boolean {
  return pathname?.startsWith(href.replace(/\/$/, "")) ?? false;
}

/** Page frame for every signed-in page: skip link, landmark navigation, logout. Pages
 * without a token are sent to the login page. */
export function Shell({ title, lede, children }: ShellProps) {
  const { ready, api, logout } = useSession();
  const router = useRouter();
  const pathname = usePathname();
  const panelId = useId();
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    if (ready && !api) router.replace("/");
  }, [ready, api, router]);

  if (!ready) return <Loading what="your session" />;
  if (!api) return <Loading what="the login page" />;

  return (
    <div className="app">
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <header className="sidebar">
        <Link href={HOME} className="brand">
          <BrandMark />
          Ripple
        </Link>
        <button
          type="button"
          className="quiet menu-toggle"
          aria-expanded={menuOpen}
          aria-controls={panelId}
          onClick={() => setMenuOpen((open) => !open)}
        >
          {menuOpen ? "Close menu" : "Menu"}
        </button>
        <div className="nav-panel" id={panelId} data-open={menuOpen}>
          <nav aria-label="Main" className="nav-groups">
            {NAV_GROUPS.map((group) => (
              <div className="nav-group" key={group.label}>
                <h2>{group.label}</h2>
                <ul>
                  {group.items.map((item) => (
                    <li key={item.href}>
                      <Link
                        href={item.href}
                        aria-current={isCurrent(pathname, item.href) ? "page" : undefined}
                        onClick={() => setMenuOpen(false)}
                      >
                        {item.label}
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </nav>
          <div className="sidebar-foot">
            <span>Ripple re-checks what it believes whenever a fact changes.</span>
            <button
              type="button"
              className="quiet small"
              onClick={() => {
                logout();
                router.replace("/");
              }}
            >
              Log out
            </button>
          </div>
        </div>
      </header>
      <main id="main" className="page">
        <div className="page-head">
          <h1>{title}</h1>
          {lede ? <p className="lede">{lede}</p> : null}
        </div>
        {children}
      </main>
    </div>
  );
}
