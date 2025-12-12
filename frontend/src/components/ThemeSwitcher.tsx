import { useTheme } from '@/contexts/ThemeContext';
import { Sun, Moon, Palette } from 'lucide-react';
import { cn } from '@/lib/utils';

export default function ThemeSwitcher() {
  const { theme, setTheme } = useTheme();

  const themes = [
    { name: 'light', icon: Sun, color: 'bg-white-smoke-100 border-dusty-taupe-300' },
    { name: 'dark', icon: Moon, color: 'bg-jet-black-900 border-jet-black-700' },
    { name: 'colorful', icon: Palette, color: 'bg-gradient-to-r from-peach-glow-400 to-frosted-mint-400 border-peach-glow-300' },
  ] as const;

  return (
    <div className="flex items-center gap-2 p-2">
      {themes.map(({ name, icon: Icon, color }) => (
        <button
          key={name}
          onClick={() => setTheme(name)}
          className={cn(
            'relative h-8 w-8 rounded-full border-2 transition-all hover:scale-110',
            color,
            theme === name
              ? 'ring-2 ring-primary ring-offset-2 ring-offset-background scale-105'
              : 'opacity-60 hover:opacity-100'
          )}
          title={`Switch to ${name} theme`}
          aria-label={`Switch to ${name} theme`}
        >
          <Icon
            className={cn(
              'absolute inset-0 m-auto h-4 w-4',
              name === 'light' ? 'text-dusty-taupe-700' : 
              name === 'dark' ? 'text-white-smoke-100' : 
              'text-white'
            )}
          />
        </button>
      ))}
    </div>
  );
}
