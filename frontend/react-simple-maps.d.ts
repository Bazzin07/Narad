declare module 'react-simple-maps' {
  import { ComponentType, CSSProperties, ReactNode } from 'react';

  interface ComposableMapProps {
    projection?: string;
    projectionConfig?: {
      center?: [number, number];
      scale?: number;
      rotate?: [number, number, number];
      parallels?: [number, number];
    };
    style?: CSSProperties;
    width?: number;
    height?: number;
    children?: ReactNode;
  }

  interface GeographiesChildrenProps {
    geographies: any[];
  }

  interface GeographiesProps {
    geography: string | object;
    children: (data: GeographiesChildrenProps) => ReactNode;
  }

  interface GeographyStyleProps {
    fill?: string;
    stroke?: string;
    strokeWidth?: number;
    outline?: string;
    cursor?: string;
    transition?: string;
  }

  interface GeographyProps {
    geography: any;
    onMouseEnter?: (event?: any) => void;
    onMouseLeave?: (event?: any) => void;
    onClick?: (event?: any) => void;
    style?: {
      default?: GeographyStyleProps;
      hover?: GeographyStyleProps;
      pressed?: GeographyStyleProps;
    };
  }

  interface ZoomableGroupProps {
    center?: [number, number];
    zoom?: number;
    minZoom?: number;
    maxZoom?: number;
    children?: ReactNode;
  }

  export const ComposableMap: ComponentType<ComposableMapProps>;
  export const Geographies: ComponentType<GeographiesProps>;
  export const Geography: ComponentType<GeographyProps>;
  export const ZoomableGroup: ComponentType<ZoomableGroupProps>;
}
