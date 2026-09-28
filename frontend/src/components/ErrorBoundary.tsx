import { Component, type ErrorInfo, type ReactNode } from 'react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Uncaught error in component:', error, errorInfo);
  }

  public render() {
    if (this.state.hasError) {
      return this.props.fallback || (
        <div className="p-6 m-4 bg-red-950/60 border border-red-500/50 rounded-xl text-red-200 text-sm max-w-xl mx-auto shadow-2xl backdrop-blur-md">
          <h3 className="font-bold text-red-100 text-base mb-1">Component Render Issue Recovered</h3>
          <p className="text-red-300 text-xs mb-3 font-mono">{this.state.error?.message || 'Unknown runtime error'}</p>
          <button 
            onClick={() => this.setState({ hasError: false })}
            className="px-3 py-1.5 bg-red-700 hover:bg-red-600 text-xs font-semibold rounded text-white transition-colors"
          >
            Reset Component
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

export default ErrorBoundary;
