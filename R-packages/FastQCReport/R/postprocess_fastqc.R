## $Id: postprocess_fastqc.R 3820 2016-05-16 14:26:29Z tfrayner $

## N.B. species would be good here as well, but requested_genome isn't all that good a surrogate.
## model.qs <- lm(median_quality_score~operator+libtype+date+read_length+paired+machine_type+multiplexed, res)

summariseQuality <- function(df) {
  .doCalc <- function(Quality, Count) {
    return(median(rep(Quality,Count))) # the median
  }
  return(.doCalc(df$Quality, df$Count))
}

meanQualityScores <- function(df) {
  .doCalc <- function(Quality, Count) {
    return(sum(Quality*Count)/sum(Count)) # the mean
  }
  return(.doCalc(df$Quality, df$Count))
}

.extractPerBaseSeqContRanges <- function(x) {
  cont <- x$Per.base.sequence.content[-c(1:2),-1]
  nan <- apply(cont, 1, function(x) any(x=='NaN'))
  cont <- cont[ complete.cases(cont) & ! nan, ]
  apply(cont, 1, function(x) as.numeric(range(x)))
}

areaUnderSeqdupeCurve <- function(x) {
  # Throw out the unduplicated and 10+ figures as they're not terribly informative.
  sum(x$Sequence.Duplication.Levels[-c(1,10), 2])
}

calcMaxBaseDiff <- function(x) {
  # Skip the first two positions as they are noisy.
  x <- .extractPerBaseSeqContRanges(x)
  max(apply(x, 2, diff))
}

calcMedianBaseDiff <- function(x) {
  # Skip the first two positions as they are noisy.
  x <- .extractPerBaseSeqContRanges(x)
  median(apply(x, 2, diff))
}

## Handle ranges such as "90-94" etc. by taking the midpoint.
.charRangeToMean <- function(x) {
  if ( is.character(x) )
    sapply(sapply(as.character(x), strsplit, '-'), function(x) { mean(as.numeric(x)) })
  else
    x
}

## Call this thusly: output <- t(sapply(fastqc, fitQualityScoreMod))
fitQualityScoreMod <- function(x) {

  ## FIXME perhaps refine this by throwing out quality scores of
  ## zero?? The tail of the decay curve will deviate from the linear
  ## model.
  data <- x$Per.base.sequence.quality
  if ( is.character(data$Base) ) {
    data$Base <- .charRangeToMean(data$Base)
  }

  ## The following model definition arrived at by trial and
  ## error. Summary residuals plot indicates little deviation from the
  ## predicted line for the majority of our sequencing lanes. Make of
  ## this what you will!
  mod <- lm(Mean~I(Base^2), data=data)
  return(mod$coefficients)
}

fitQualityScoreVarMod <- function(x) {

  ## Fit a model to describe the *variance* in quality scores
  x <- x$Per.base.sequence.quality
  if ( is.character(x$Base) ) {
    x$Base <- .charRangeToMean(x$Base)
  }
  data <- data.frame(Base=x$Base, Range=x$`90th Percentile` - x$`10th Percentile`)

  ## The following model definition arrived at by trial and error. As
  ## for the regular median-score model above, summary residuals plot
  ## indicates little deviation from the predicted line for the
  ## majority of our sequencing lanes.
  mod <- lm(Range~I(Base^2), data=data)
  return(mod$coefficients)
}

fitKmerScoreMod <- function(x) {
  if ( nrow(x$Kmer.Content) > 2 ) {
    i <- 1/sqrt(x$Kmer.Content[,3])
    j <- 1:length(i) - 1
    return(lm(i ~ j))
  } else {
    return(NA)
  }
}

fitKmerScore <- function(x) {
  mod <- fitKmerScoreMod(x)
  if (class(mod) != 'lm')
    return(0)
  else
    return(mod$coefficients[2]) # take the gradient
}

perSeqGCDeviation <- function(x) {
  gcont <- x$Per.sequence.GC.content
  params <- calcTheoreticalGCDistParams(gcont, gcont$`GC Content`)
  totalcount <- sum(gcont$Count)
  diffs <- apply(gcont, 1, function(x) {
    abs(dnorm(x[1], mean=params$mean, sd=params$sd) - x[2]/totalcount)
  })
  sum(diffs) / 2 ## Max theoretical is 2x area under normal curve? 0.3 would be flagged as bad by fastqc.
}

medianGCContent <- function(x) {
  gc <- as.numeric(x$Per.base.GC.content[,'%GC'])
  gc <- gc[ ! is.nan(gc) ]
  median(gc, na.rm=TRUE)
}

regularisedFastqcMatrix <- function(fastqc, cl, SEQLEN=36) {

  .addValues <- function(x, vec, v, n, name) {
    r <- (n+1):(n+SEQLEN)
    vec[r] <- 0
    v <- v[1:min(length(v), SEQLEN)]
    vec[(n+1):(n+length(v))] <- v
    names(vec)[r] <- paste(name, 1:SEQLEN, sep='')
    return(vec)
  }
  
  .fastqcVector <- function(x) {

    # Note that numvars *must* be kept in sync with the operations below.
    numvars=(SEQLEN*7)+15

    vec <- vector(length=numvars, mode='numeric')
    n <- 0 # The previous hindmost vec index.

    # Quality scores, up to SEQLEN, with zeroes for missing data.
    vec <- .addValues(x, vec, x$Per.base.sequence.quality$Mean, n, name='QS')
    n <- n+SEQLEN

    # Our overall median_quality_score, for good measure. Expensive
    # median calculation.
    vec[n+1] <- summariseQuality(x$Per.sequence.quality.scores)
    names(vec)[n+1] <- 'medQS'
    n <- n+1

    # Per-base sequence content; this is slightly redundant but too
    # bad. Again, we're forced to pad with zeroes.
    for ( base in c('G','A','T','C') ) {
      vec <- .addValues(x, vec, x$Per.base.sequence.content[,base], n, name=paste('base', base, sep=''))
      n <- n+SEQLEN
    }

    # Per-base GC content; again, pretty redundant.
    vec <- .addValues(x, vec, x$Per.base.GC.content[,'%GC'], n, name='GCcont')
    n <- n+SEQLEN

    # Deviation from the normal as calculated above.
    vec[n+1] <- perSeqGCDeviation(x)
    names(vec)[n+1] <- 'gcDev'
    n <- n+1

    # N-content, zero padded.
    vec <- .addValues(x, vec, x$Per.base.N.content[,'N-Count'], n, name='Ncont')
    n <- n+SEQLEN

    # Sequence duplication levels
    vec[(n+1):(n+9)] <- x$Sequence.Duplication.Levels[1:9, 'Relative count']
    names(vec)[(n+1):(n+9)] <- paste('Dupe', 1:9, sep='')
    n <- n+9

    # A nominal sequence duplication score.
    vec[n+1] <- areaUnderSeqdupeCurve(x)
    names(vec)[n+1] <- 'seqDupeScore'
    n <- n+1

    # Kmer content score.
    vec[n+1] <- fitKmerScore(x)
    names(vec)[n+1] <- 'kmerScore'
    n <- n+1

    # Median and max base differences.
    vec[n+1] <- calcMedianBaseDiff(x)
    vec[n+2] <- calcMaxBaseDiff(x)
    names(vec)[n+1:2] <- c('medBaseDiff','maxBaseDiff')
    n <- n+2

    # Catch-all to make sure we're really numeric (lame FIXME).
    names <- names(vec)
    vec <- as.numeric(vec)
    names(vec) <- names
    return(vec)
  }

  if ( ! missing(cl) ) {
    requireNamespace('snow')
    mat <- snow::parSapply(cl, fastqc, .fastqcVector)
  }
  else {
    mat <- sapply(fastqc, .fastqcVector)
  }

  return(mat)
}

## This is actually quite generic and could be added to MyLib.
plotPCADensities <- function(pr, range=1:ncol(pr$x), variable, data, cols=NULL, ...) {
  stopifnot(variable %in% colnames(data))

  .getColRange <- function(n) {

    if ( is.null(cols) ) {
      if ( n > 9 ) {
        mycols <- colorRampPalette(brewer.pal(9, 'Set1'))(n)
      }
      else {
        mycols <- RColorBrewer::brewer.pal(min(3, n), 'Set1')
      }
    }
    else {
      mycols <- cols
    }
    return(mycols)
  }

  for (compnum in range) {
    x <- split(pr$x[, compnum], data[,variable])
    m <- which.max(sapply(x, length))
    d <- density(x[[m]])

    res <- matrix(NA, ncol=length(x), nrow=length(d$y))
    res[,m] <- d$y
    for ( n in (1:length(x))[-m] ) {
      e <- density(x[[n]], bw=d$bw)
      res[,n] <- e$y * (length(x[[n]])/length(x[[m]]))
    }

    mycols <- .getColRange(length(x))
    matplot(d$x, res, col=mycols, type='l', xlab='Component Value', ylab='Density',
            main=sprintf("Component %d", compnum), ...)
  }

  # Takes advantage of R variable scoping when exiting loops.
  plot.new()
  legend('topleft', legend=paste(variable, names(x), sep=': '), fill=mycols)

  invisible()
}
