```bash
(relay) vineet_kushwaha1@cloudshell:~/relay$ gcloud storage ls gs://vineetk/
gs://vineetk/jtd/
gs://vineetk/uiux/
gs://vineetk/vois_hub/
gs://vineetk/vois_shield/
```
```bash
(relay) vineet_kushwaha1@cloudshell:~/relay$ gcloud storage ls gs://vineetk/vois_shield/src/Pages/
gs://vineetk/vois_shield/src/Pages/Campaigns/
gs://vineetk/vois_shield/src/Pages/DashboardAndAnalytics/
gs://vineetk/vois_shield/src/Pages/EmailIDsandDomains/
gs://vineetk/vois_shield/src/Pages/GamificationEngine/
gs://vineetk/vois_shield/src/Pages/HomeScreen/
gs://vineetk/vois_shield/src/Pages/LandingPage/
gs://vineetk/vois_shield/src/Pages/LandingPageCatalogue/
gs://vineetk/vois_shield/src/Pages/RequestsAndApprovals/
gs://vineetk/vois_shield/src/Pages/Scenarios/
gs://vineetk/vois_shield/src/Pages/StartCampaign/
gs://vineetk/vois_shield/src/Pages/Training/
gs://vineetk/vois_shield/src/Pages/UserDLs/
gs://vineetk/vois_shield/src/Pages/UserProfileandPointsScoreing/
```
```bash
(relay) vineet_kushwaha1@cloudshell:~/relay$ uv run relay sync ~/security-awareness-platform/frontend/VShield/src/Pages/Training/ "gcloud storage gs://vineetk/vois_shield/src/Pages/Training" --dry-run
[relay] Resolving endpoints:
    Source:      /home/vineet_kushwaha1/security-awareness-platform/frontend/VShield/src/Pages/Training/ [LOCAL]
    Destination: gcloud storage gs://vineetk/vois_shield/src/Pages/Training [GCS]

ACTION       | PATH                           | ORIGIN / DETAIL
-----------------------------------------------------------------
ADDED        | rename_images.py               | 
DELETED      | components/utility/types.js    | 
MODIFIED     | Training.jsx                   | 
MODIFIED     | TrainingContext.jsx            | 
MODIFIED     | TrainingLandingPage.jsx        | 
MODIFIED     | components/LmsMainContent.jsx  | 
MODIFIED     | components/modals/PathwaySequencePlayerModal.jsx | 
MODIFIED     | InvidualTrainings/IndividualPackages/IndividualPackagesGallery.jsx | 
MODIFIED     | InvidualTrainings/IndividualPackages/CreateNewPackages.jsx | 
UNCHANGED    | TrainingCertificate.json       | 
UNCHANGED    | TrainingPath.json              | 
UNCHANGED    | Training.css                   | 
UNCHANGED    | TrainingQuiz.json              | 
UNCHANGED    | TrainingVideos.json            | 
UNCHANGED    | MyTrainingData.json            | 
UNCHANGED    | TrainingPath/TrainingPathLandingPage.jsx | 
UNCHANGED    | TrainingPath/TrainingPathAllGallery/TrainingPathAllGallery.jsx | 
UNCHANGED    | TrainingPath/TrainingPathCreateNew/TrainingPathCreateNew.jsx | 
UNCHANGED    | components/LmsModals.jsx       | 
UNCHANGED    | components/LmsLeftSidebar.jsx  | 
UNCHANGED    | components/utility/colorHelpers.js | 
UNCHANGED    | components/utility/db.js       | 
UNCHANGED    | components/utility/zipHelpers.js | 
UNCHANGED    | components/shared/LmsControlHub.jsx | 
UNCHANGED    | components/shared/GlassmorphicBackdrop.jsx | 
UNCHANGED    | components/shared/VideoThumbnail.jsx | 
UNCHANGED    | components/shared/CertificateThumbnail.jsx | 
UNCHANGED    | components/modals/helpers.js   | 
UNCHANGED    | components/modals/Modals.jsx   | 
UNCHANGED    | components/modals/QuizTakerModal.jsx | 
UNCHANGED    | components/modals/CertificateViewerModal.jsx | 
UNCHANGED    | components/modals/VideoPlayerModal.jsx | 
UNCHANGED    | components/cards/TrainingCertificateCard.jsx | 
UNCHANGED    | components/cards/TrainingPathCard.jsx | 
UNCHANGED    | components/cards/TrainingVideoCard.jsx | 
UNCHANGED    | components/cards/HubClayCard.jsx | 
UNCHANGED    | components/cards/TrainingQuizCard.jsx | 
UNCHANGED    | InvidualTrainings/InvidualTrainingsLandingPage.jsx | 
UNCHANGED    | InvidualTrainings/IndividualVideos/IndividualVideosGallery.jsx | 
UNCHANGED    | InvidualTrainings/IndividualVideos/CreateNewVideos.jsx | 
UNCHANGED    | InvidualTrainings/IndividualCertificates/CreateNewCertificates.jsx | 
UNCHANGED    | InvidualTrainings/IndividualCertificates/IndividualCertificatesGallery.jsx | 
UNCHANGED    | InvidualTrainings/IndividualQuiz/IndividualQuizGallery.jsx | 
UNCHANGED    | InvidualTrainings/IndividualQuiz/CreateNewQuiz.jsx | 
UNCHANGED    | RequestsAndApprovals/RequestsAndApprovalsLandingPage.jsx | 
UNCHANGED    | RequestsAndApprovals/components/RejectedPathsGallery.jsx | 
UNCHANGED    | RequestsAndApprovals/components/RequestedQueueGallery.jsx | 
UNCHANGED    | RequestsAndApprovals/components/RejectionNoteWindow.jsx | 
UNCHANGED    | RequestsAndApprovals/components/ApprovedPathsGallery.jsx | 
UNCHANGED    | RequestsAndApprovals/components/ApprovalQueueGallery.jsx | 
UNCHANGED    | TrainingReport/TrainingReportLandingPage.jsx | 

Planned changes:
  • 1 to add
  • 7 to modify
  • 1 untracked on destination (kept, use --delete to prune)

[dry-run] Dry run active. No changes applied.
```
```bash
(relay) vineet_kushwaha1@cloudshell:~/relay$ uv run relay sync ~/security-awareness-platform/frontend/VShield/src/Pages/Training/ "gcloud storage gs://vineetk/vois_shield/src/Pages/Training" --delete
[relay] Resolving endpoints:
    Source:      /home/vineet_kushwaha1/security-awareness-platform/frontend/VShield/src/Pages/Training/ [LOCAL]
    Destination: gcloud storage gs://vineetk/vois_shield/src/Pages/Training [GCS]

ACTION       | PATH                           | ORIGIN / DETAIL
-----------------------------------------------------------------
ADDED        | rename_images.py               | 
DELETED      | components/utility/types.js    | 
MODIFIED     | Training.jsx                   | 
MODIFIED     | TrainingContext.jsx            | 
MODIFIED     | TrainingLandingPage.jsx        | 
MODIFIED     | components/LmsMainContent.jsx  | 
MODIFIED     | components/modals/PathwaySequencePlayerModal.jsx | 
MODIFIED     | InvidualTrainings/IndividualPackages/IndividualPackagesGallery.jsx | 
MODIFIED     | InvidualTrainings/IndividualPackages/CreateNewPackages.jsx | 
UNCHANGED    | TrainingCertificate.json       | 
UNCHANGED    | TrainingPath.json              | 
UNCHANGED    | Training.css                   | 
UNCHANGED    | TrainingQuiz.json              | 
UNCHANGED    | TrainingVideos.json            | 
UNCHANGED    | MyTrainingData.json            | 
UNCHANGED    | TrainingPath/TrainingPathLandingPage.jsx | 
UNCHANGED    | TrainingPath/TrainingPathAllGallery/TrainingPathAllGallery.jsx | 
UNCHANGED    | TrainingPath/TrainingPathCreateNew/TrainingPathCreateNew.jsx | 
UNCHANGED    | components/LmsModals.jsx       | 
UNCHANGED    | components/LmsLeftSidebar.jsx  | 
UNCHANGED    | components/utility/colorHelpers.js | 
UNCHANGED    | components/utility/db.js       | 
UNCHANGED    | components/utility/zipHelpers.js | 
UNCHANGED    | components/shared/LmsControlHub.jsx | 
UNCHANGED    | components/shared/GlassmorphicBackdrop.jsx | 
UNCHANGED    | components/shared/VideoThumbnail.jsx | 
UNCHANGED    | components/shared/CertificateThumbnail.jsx | 
UNCHANGED    | components/modals/helpers.js   | 
UNCHANGED    | components/modals/Modals.jsx   | 
UNCHANGED    | components/modals/QuizTakerModal.jsx | 
UNCHANGED    | components/modals/CertificateViewerModal.jsx | 
UNCHANGED    | components/modals/VideoPlayerModal.jsx | 
UNCHANGED    | components/cards/TrainingCertificateCard.jsx | 
UNCHANGED    | components/cards/TrainingPathCard.jsx | 
UNCHANGED    | components/cards/TrainingVideoCard.jsx | 
UNCHANGED    | components/cards/HubClayCard.jsx | 
UNCHANGED    | components/cards/TrainingQuizCard.jsx | 
UNCHANGED    | InvidualTrainings/InvidualTrainingsLandingPage.jsx | 
UNCHANGED    | InvidualTrainings/IndividualVideos/IndividualVideosGallery.jsx | 
UNCHANGED    | InvidualTrainings/IndividualVideos/CreateNewVideos.jsx | 
UNCHANGED    | InvidualTrainings/IndividualCertificates/CreateNewCertificates.jsx | 
UNCHANGED    | InvidualTrainings/IndividualCertificates/IndividualCertificatesGallery.jsx | 
UNCHANGED    | InvidualTrainings/IndividualQuiz/IndividualQuizGallery.jsx | 
UNCHANGED    | InvidualTrainings/IndividualQuiz/CreateNewQuiz.jsx | 
UNCHANGED    | RequestsAndApprovals/RequestsAndApprovalsLandingPage.jsx | 
UNCHANGED    | RequestsAndApprovals/components/RejectedPathsGallery.jsx | 
UNCHANGED    | RequestsAndApprovals/components/RequestedQueueGallery.jsx | 
UNCHANGED    | RequestsAndApprovals/components/RejectionNoteWindow.jsx | 
UNCHANGED    | RequestsAndApprovals/components/ApprovedPathsGallery.jsx | 
UNCHANGED    | RequestsAndApprovals/components/ApprovalQueueGallery.jsx | 
UNCHANGED    | TrainingReport/TrainingReportLandingPage.jsx | 

Planned changes:
  • 1 to add
  • 7 to modify
  • 1 to delete

Proceed with deletion and sync? [y/N]: y

Sync completed successfully:
  • 8 transferred
  • 1 deleted
```
```bash
(relay) vineet_kushwaha1@cloudshell:~/relay$ uv run relay sync ~/security-awareness-platform/frontend/VShield/src/Pages/Training/ "gcloud storage gs://vineetk/vois_shield/src/Pages/Training" --dry-run
[relay] Resolving endpoints:
    Source:      /home/vineet_kushwaha1/security-awareness-platform/frontend/VShield/src/Pages/Training/ [LOCAL]
    Destination: gcloud storage gs://vineetk/vois_shield/src/Pages/Training [GCS]

ACTION       | PATH                           | ORIGIN / DETAIL
-----------------------------------------------------------------
UNCHANGED    | TrainingCertificate.json       | 
UNCHANGED    | TrainingPath.json              | 
UNCHANGED    | rename_images.py               | 
UNCHANGED    | Training.jsx                   | 
UNCHANGED    | Training.css                   | 
UNCHANGED    | TrainingContext.jsx            | 
UNCHANGED    | TrainingQuiz.json              | 
UNCHANGED    | TrainingLandingPage.jsx        | 
UNCHANGED    | TrainingVideos.json            | 
UNCHANGED    | MyTrainingData.json            | 
UNCHANGED    | TrainingPath/TrainingPathLandingPage.jsx | 
UNCHANGED    | TrainingPath/TrainingPathAllGallery/TrainingPathAllGallery.jsx | 
UNCHANGED    | TrainingPath/TrainingPathCreateNew/TrainingPathCreateNew.jsx | 
UNCHANGED    | components/LmsModals.jsx       | 
UNCHANGED    | components/LmsMainContent.jsx  | 
UNCHANGED    | components/LmsLeftSidebar.jsx  | 
UNCHANGED    | components/utility/colorHelpers.js | 
UNCHANGED    | components/utility/db.js       | 
UNCHANGED    | components/utility/zipHelpers.js | 
UNCHANGED    | components/shared/LmsControlHub.jsx | 
UNCHANGED    | components/shared/GlassmorphicBackdrop.jsx | 
UNCHANGED    | components/shared/VideoThumbnail.jsx | 
UNCHANGED    | components/shared/CertificateThumbnail.jsx | 
UNCHANGED    | components/modals/helpers.js   | 
UNCHANGED    | components/modals/PathwaySequencePlayerModal.jsx | 
UNCHANGED    | components/modals/Modals.jsx   | 
UNCHANGED    | components/modals/QuizTakerModal.jsx | 
UNCHANGED    | components/modals/CertificateViewerModal.jsx | 
UNCHANGED    | components/modals/VideoPlayerModal.jsx | 
UNCHANGED    | components/cards/TrainingCertificateCard.jsx | 
UNCHANGED    | components/cards/TrainingPathCard.jsx | 
UNCHANGED    | components/cards/TrainingVideoCard.jsx | 
UNCHANGED    | components/cards/HubClayCard.jsx | 
UNCHANGED    | components/cards/TrainingQuizCard.jsx | 
UNCHANGED    | InvidualTrainings/InvidualTrainingsLandingPage.jsx | 
UNCHANGED    | InvidualTrainings/IndividualPackages/IndividualPackagesGallery.jsx | 
UNCHANGED    | InvidualTrainings/IndividualPackages/CreateNewPackages.jsx | 
UNCHANGED    | InvidualTrainings/IndividualVideos/IndividualVideosGallery.jsx | 
UNCHANGED    | InvidualTrainings/IndividualVideos/CreateNewVideos.jsx | 
UNCHANGED    | InvidualTrainings/IndividualCertificates/CreateNewCertificates.jsx | 
UNCHANGED    | InvidualTrainings/IndividualCertificates/IndividualCertificatesGallery.jsx | 
UNCHANGED    | InvidualTrainings/IndividualQuiz/IndividualQuizGallery.jsx | 
UNCHANGED    | InvidualTrainings/IndividualQuiz/CreateNewQuiz.jsx | 
UNCHANGED    | RequestsAndApprovals/RequestsAndApprovalsLandingPage.jsx | 
UNCHANGED    | RequestsAndApprovals/components/RejectedPathsGallery.jsx | 
UNCHANGED    | RequestsAndApprovals/components/RequestedQueueGallery.jsx | 
UNCHANGED    | RequestsAndApprovals/components/RejectionNoteWindow.jsx | 
UNCHANGED    | RequestsAndApprovals/components/ApprovedPathsGallery.jsx | 
UNCHANGED    | RequestsAndApprovals/components/ApprovalQueueGallery.jsx | 
UNCHANGED    | TrainingReport/TrainingReportLandingPage.jsx | 

Everything is up to date. Zero changes needed.
(relay) vineet_kushwaha1@cloudshell:~/relay$ 
```