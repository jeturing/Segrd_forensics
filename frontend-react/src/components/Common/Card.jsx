import React from 'react';
import classNames from 'classnames';

export default function Card({
  children,
  title,
  subtitle,
  icon: Icon = null,
  actions = null,
  className,
  ...props
}) {
  // Renderiza el icono - puede ser un componente React o un string (emoji)
  const renderIcon = () => {
    if (!Icon) return null;
    // Si es un string (emoji), renderizarlo como texto
    if (typeof Icon === 'string') {
      return <span className="text-xl">{Icon}</span>;
    }
    // Si es un componente React, renderizarlo normalmente
    return <Icon className="w-6 h-6 text-blue-400" />;
  };

  return (
    <div className={classNames('card', className)} {...props}>
      {(title || Icon || actions) && (
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-700">
          <div className="flex items-center gap-3">
            {renderIcon()}
            <div>
              {title && <h3 className="font-semibold text-lg">{title}</h3>}
              {subtitle && <p className="text-sm text-gray-400">{subtitle}</p>}
            </div>
          </div>
          {actions && <div className="flex gap-2">{actions}</div>}
        </div>
      )}
      <div className="px-6 py-4">
        {children}
      </div>
    </div>
  );
}
