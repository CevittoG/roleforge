import * as React from 'react';
import { ChevronDown } from 'lucide-react';
import { cn } from '@/lib/cn';

export type SelectProps = React.SelectHTMLAttributes<HTMLSelectElement>;

export const Select = React.forwardRef<HTMLSelectElement, SelectProps>(
  ({ className, children, ...props }, ref) => (
    <div className="relative">
      <select
        ref={ref}
        className={cn(
          'flex h-11 min-h-touch w-full appearance-none rounded-md border border-input bg-background ' +
            'pl-3 pr-9 text-base shadow-sm ' +
            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ' +
            'disabled:cursor-not-allowed disabled:opacity-50',
          className,
        )}
        {...props}
      >
        {children}
      </select>
      <ChevronDown
        className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
        aria-hidden="true"
      />
    </div>
  ),
);
Select.displayName = 'Select';
