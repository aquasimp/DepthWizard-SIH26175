import { useEffect, useState } from 'react';
import { JobStatusPage } from './pages/JobStatusPage';
import { UploadPage } from './pages/UploadPage';
import { ValidatePage } from './pages/ValidatePage';
import { ViewerPage } from './pages/ViewerPage';

export type PageView = 'upload' | 'status' | 'viewer' | 'validate';

export function App() {
  const [currentPage, setCurrentPage] = useState<PageView>('upload');
  const [activeJobId, setActiveJobId] = useState<string | null>(null);

  // Read URL query params on mount for direct link navigation
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const jobParam = params.get('job');
    const pageParam = params.get('page') as PageView | null;

    if (jobParam) {
      setActiveJobId(jobParam);
      if (pageParam && ['status', 'viewer', 'validate'].includes(pageParam)) {
        setCurrentPage(pageParam);
      } else {
        setCurrentPage('viewer');
      }
    }
  }, []);

  const navigateTo = (page: PageView, jobId?: string) => {
    if (jobId) setActiveJobId(jobId);
    setCurrentPage(page);

    const url = new URL(window.location.href);
    if (jobId) url.searchParams.set('job', jobId);
    else url.searchParams.delete('job');
    url.searchParams.set('page', page);
    window.history.pushState({}, '', url.toString());
  };

  if (currentPage === 'viewer' && activeJobId) {
    return (
      <ViewerPage
        jobId={activeJobId}
        onNavigateBack={() => navigateTo('upload')}
        onNavigateValidate={(id) => navigateTo('validate', id)}
      />
    );
  }

  if (currentPage === 'status' && activeJobId) {
    return (
      <JobStatusPage
        jobId={activeJobId}
        onOpenViewer={(id) => navigateTo('viewer', id)}
        onNavigateHome={() => navigateTo('upload')}
        onNavigateValidate={(id) => navigateTo('validate', id)}
      />
    );
  }

  if (currentPage === 'validate' && activeJobId) {
    return (
      <ValidatePage
        jobId={activeJobId}
        onNavigateBack={() => navigateTo('viewer', activeJobId)}
        onNavigateHome={() => navigateTo('upload')}
        onNavigateStatus={(id) => navigateTo('status', id)}
      />
    );
  }

  return (
    <UploadPage
      onJobSelect={(id) => navigateTo('viewer', id)}
      onJobCreated={(id) => navigateTo('status', id)}
      onNavigateValidate={(id) => navigateTo('validate', id)}
    />
  );
}

export default App;
