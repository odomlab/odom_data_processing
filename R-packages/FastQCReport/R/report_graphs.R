## $Id: report_graphs.R 3031 2013-05-01 14:08:59Z tfrayner $
##
## Core report graph functions.

plotPerSequenceGC <- function(fq) {

  gc <- fq$Per.sequence.GC.content

  ## Needs theoretical GC distribution overlay
  gc$`Theoretical Distribution` <- .deriveTheoreticalGCDist(gc, points=gc$`GC Content`)
  colnames(gc)[1:2] <- c('GC', 'GC count per read')

  pl <- .genericGGLinePlot(gc, xcol='GC', cols=c('red', 'blue')) +
    labs(title="GC distribution over all sequences",
         x="Mean GC content (%)",
         y="Count")
  
  return(pl)
}

plotPerSequenceQuality <- function(fq) {

  qs <- fq$Per.sequence.quality.scores
  colnames(qs) <- c('quality', 'Average quality per read')

  pl <- .genericGGLinePlot(qs, xcol='quality', cols='red') +
    labs(title="Quality score distribution over all sequences",
         x="Mean Sequence Quality (Phred Score)",
         y="Count")
  
  return(pl)  
}

plotPerBaseSequenceContent <- function(fq) {

  sc <- fq$Per.base.sequence.content

  pl <- .genericGGLinePlot(sc, xcol='Base', cols=c('black', 'green', 'red', 'blue')) +
    labs(title="Sequence content across all bases",
         x="Position in read (bp)",
         y="Base content (%)") +
    scale_y_continuous(limits=c(0, 100))
  
  return(pl)
}

plotPerBaseGC <- function(fq) {

  gc <- fq$Per.base.GC.content

  pl <- .genericGGLinePlot(gc, xcol='Base', cols=c('red')) +
    labs(title="GC content across all bases",
         x="Position in read (bp)",
         y="GC content (%)") +
    scale_y_continuous(limits=c(0, 100))

  return(pl)
}

plotPerBaseN <- function(fq) {

  nc <- fq$Per.base.N.content
  colnames(nc) <- c('Base', '%N')

  pl <- .genericGGLinePlot(nc, xcol='Base', cols=c('red')) +
    labs(title="N content across all bases",
         x="Position in read (bp)",
         y="N content (%)") +
    scale_y_continuous(limits=c(0, 100))

  return(pl)
}

.genericGGLinePlot <- function(df, xcol=NULL, cols=NULL) {

  ## Handles data frame melt() call and mapping colours to aesthetics.
  if ( is.null(xcol) )
    xcol <- colnames(df)[1]
  w <- colnames(df) == xcol
  xcol <- make.names(xcol)
  colnames(df)[w] <- xcol

  ncol <- ncol(df) - 1

  df <- melt(df, id=xcol)
  pl <- ggplot(df, aes_string(x=xcol)) +
    geom_line(aes_string(y='value', color='variable'))+
    scale_color_manual(name='',
                       values=cols[1:ncol])
  return(pl)
}

calcTheoreticalGCDistParams <- function(gc, points=1:101) {

  ## This code derived from the FastQC java code.
  gcDist <- gc$`Count`

  ## Simple mode estimate.
  firstMode <- which.max(gcDist)

  ## More robust mode estimate. This includes a check for extreme
  ## skewing where parts of the curve above 95% of the firstMode lie
  ## at the very edge of the 0-100% scale, in which case we just take
  ## the original mode.
  w <- gcDist > 0.95 * gcDist[firstMode]
  if (w[1] || w[length(w)])
    mode <- firstMode
  else
    mode <- mean(gc$`GC Content`[w])

  ## Calculate the appropriate model standard deviation.
  stdev = 0
  for ( i in 1:length(gcDist) ) {
    stdev = stdev + ((( i-mode )^2) * gcDist[i])
  }
  denom <- sum(gcDist)-1
  sd <- sqrt(stdev/denom)

  return(list(mean=mode, sd=sd, denom=denom))
}

.deriveTheoreticalGCDist <- function(gc, points=1:101) {

  params <- calcTheoreticalGCDistParams(gc, points)

  ## Return points suitable for plotting.
  return(dnorm(points, mean=params$mean, sd=params$sd) * params$denom)
}
