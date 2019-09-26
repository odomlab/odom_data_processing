## $Id$
##
## Code used to define acceptance tests for incoming fastq/fastqc data.

## This would be the main yes/no function.
acceptQC <- function(fastqc, funlist=c(acceptUniqReadFrac,
                               acceptReadFracAboveQuality,
                               acceptLowestMedian3primeQuality)) {
  return(  all( sapply(funlist, function(fun) fun(fastqc)) ) )
}

## A set of recommended thresholds are defined by the following functions.
acceptUniqReadFrac <- function(fastqc, threshold=0.9) {
  return(getUniqReadFrac(fastqc) >= threshold)
}

acceptReadFracAboveQuality <- function(fastqc, threshold=0.75, qc_cutoff=30) {
  return(getReadFracAboveQuality(fastqc, qc_cutoff) >= threshold)
}

acceptLowestMedian3primeQuality <- function(fastqc, qc_cutoff=24) {
  return(getLowestMedian3primeQuality(fastqc) >= qc_cutoff)
}

## The actual calculations are performed below. Inputs are the outputs
## of parseFastQC. FIXME maybe make this a set of S4 classes and
## methods?
getUniqReadFrac <- function(fastqc) {

  ## Assumes the report counts each duplicate read towards the bins
  ## for 2,3,4...; this seems in line with the numbers reported
  ## following MarkDuplicates.
  x <- fastqc$Sequence.Duplication.Levels
  uniq <- x[1,2]/sum(x[,2])
  return(uniq)
}

getReadFracAboveQuality <- function(fastqc, qc_cutoff=30) {

  ## Fraction of reads with overall quality scores greater than qc_cutoff.
  x <- fastqc$Per.sequence.quality.scores
  x[,1] <- as.numeric(x[,1])
  good <- sum(x[ x[,1] >= qc_cutoff, 2])/sum(x[,2])
  return(good)
}

getLowestMedian3primeQuality <- function(fastqc) {

  ## Simply the lowest median quality score for the 3' base position
  ## in the reads, to attempt to control for premature drops in
  ## quality. This assumes all reads are of the same length.
  x <- fastqc$Per.base.sequence.quality
  lowestmed <- x[ nrow(x), 'Median' ]
  return(lowestmed)
}
