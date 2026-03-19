// JHBridge - Filter Dropdown Component
import { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Filter, X, Check, ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";

export const FilterDropdown = ({
  filters = [],
  activeFilters = {},
  onChange,
  trigger,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [localFilters, setLocalFilters] = useState(activeFilters);
  const dropdownRef = useRef(null);

  // Close on outside click
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setIsOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Sync local filters with props
  useEffect(() => {
    setLocalFilters(activeFilters);
  }, [activeFilters]);

  const handleToggleOption = (filterKey, optionValue) => {
    setLocalFilters(prev => {
      const currentValues = prev[filterKey] || [];
      const newValues = currentValues.includes(optionValue)
        ? currentValues.filter(v => v !== optionValue)
        : [...currentValues, optionValue];
      return { ...prev, [filterKey]: newValues };
    });
  };

  const handleApply = () => {
    onChange(localFilters);
    setIsOpen(false);
  };

  const handleClearAll = () => {
    const cleared = {};
    filters.forEach(f => { cleared[f.key] = []; });
    setLocalFilters(cleared);
    onChange(cleared);
  };

  const activeCount = Object.values(activeFilters).flat().length;

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Trigger Button */}
      {trigger ? (
        <div onClick={() => setIsOpen(!isOpen)}>{trigger}</div>
      ) : (
        <Button
          variant="outline"
          size="sm"
          className="gap-1.5"
          onClick={() => setIsOpen(!isOpen)}
          data-testid="filter-trigger-btn"
        >
          <Filter className="w-3.5 h-3.5" />
          Filter
          {activeCount > 0 && (
            <span className="ml-1 px-1.5 py-0.5 text-[10px] font-semibold bg-primary text-primary-foreground rounded">
              {activeCount}
            </span>
          )}
          <ChevronDown className={cn("w-3.5 h-3.5 transition-transform", isOpen && "rotate-180")} />
        </Button>
      )}

      {/* Dropdown */}
      {isOpen && (
        <div 
          className="absolute top-full left-0 mt-1 w-72 bg-card border border-border rounded-lg shadow-lg z-50 animate-in fade-in slide-in-from-top-2 duration-200"
          data-testid="filter-dropdown"
        >
          {/* Header */}
          <div className="flex items-center justify-between p-3 border-b border-border">
            <span className="text-sm font-semibold">Filters</span>
            <button
              onClick={() => setIsOpen(false)}
              className="p-1 rounded hover:bg-muted transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Filter Sections */}
          <div className="max-h-80 overflow-y-auto p-2">
            {filters.map((filter, idx) => (
              <div key={filter.key} className={cn("py-2", idx > 0 && "border-t border-border")}>
                <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider px-2 mb-2">
                  {filter.label}
                </div>
                <div className="space-y-1">
                  {filter.options.map((option) => {
                    const isSelected = (localFilters[filter.key] || []).includes(option.value);
                    return (
                      <button
                        key={option.value}
                        onClick={() => handleToggleOption(filter.key, option.value)}
                        className={cn(
                          "w-full flex items-center gap-2 px-2 py-1.5 rounded text-sm transition-colors",
                          isSelected ? "bg-primary/10 text-primary" : "hover:bg-muted"
                        )}
                        data-testid={`filter-option-${filter.key}-${option.value}`}
                      >
                        <div className={cn(
                          "w-4 h-4 rounded border flex items-center justify-center",
                          isSelected ? "bg-primary border-primary" : "border-border"
                        )}>
                          {isSelected && <Check className="w-3 h-3 text-primary-foreground" />}
                        </div>
                        <span className="flex-1 text-left">{option.label}</span>
                        {option.count !== undefined && (
                          <span className="text-xs text-muted-foreground font-mono">{option.count}</span>
                        )}
                      </button>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>

          {/* Footer */}
          <div className="flex items-center justify-between p-3 border-t border-border bg-muted/30">
            <Button
              variant="ghost"
              size="sm"
              onClick={handleClearAll}
              className="text-xs"
              data-testid="filter-clear-all"
            >
              Clear All
            </Button>
            <Button
              size="sm"
              onClick={handleApply}
              className="bg-navy hover:bg-navy-light"
              data-testid="filter-apply"
            >
              Apply Filters
            </Button>
          </div>
        </div>
      )}
    </div>
  );
};

export default FilterDropdown;
