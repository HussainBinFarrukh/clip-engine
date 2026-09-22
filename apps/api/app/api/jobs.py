import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.job import Job, JobState
from app.models.source_video import SourceVideo
from app.schemas.job import JobRead
from app.services.job_queue import dispatch_job

router = APIRouter(tags=["jobs"])


@router.get("/jobs/{job_id}", response_model=JobRead)
def get_job(job_id: uuid.UUID, db: Session = Depends(get_db)) -> Job:
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/projects/{project_id}/jobs", response_model=list[JobRead])
def list_project_jobs(project_id: uuid.UUID, db: Session = Depends(get_db)) -> list[Job]:
    return list(
        db.scalars(
            select(Job)
            .join(SourceVideo, Job.source_video_id == SourceVideo.id)
            .where(SourceVideo.project_id == project_id)
            .order_by(Job.created_at.desc())
        )
    )


@router.post("/jobs/{job_id}/retry", response_model=JobRead)
def retry_job(job_id: uuid.UUID, db: Session = Depends(get_db)) -> Job:
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.state != JobState.FAILED:
        raise HTTPException(status_code=400, detail="Only failed jobs can be retried")

    job.state = JobState.QUEUED
    job.error_code = None
    job.error_message = None
    db.commit()
    db.refresh(job)

    dispatch_job(job.id)

    db.refresh(job)
    return job
